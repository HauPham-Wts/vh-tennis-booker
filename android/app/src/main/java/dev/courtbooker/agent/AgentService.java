package dev.courtbooker.agent;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.Intent;
import android.graphics.Path;
import android.net.LocalServerSocket;
import android.net.LocalSocket;
import android.os.SystemClock;
import android.system.Os;
import android.system.OsConstants;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * Lets the PC read and tap the screen. Commands come as one JSON object per line on the
 * abstract socket {@value #SOCKET} (reached with {@code adb forward tcp:N
 * localabstract:court-agent}); each gets one JSON line back with the same {@code id},
 * {@code ok} and, when {@code ok} is false, {@code error}.
 *
 * <p>Android unbinds the service while uiautomator2 runs and binds a new instance when it
 * stops, so the socket belongs to the bound instance: opened when it connects, closed when
 * it is unbound.
 */
public class AgentService extends AccessibilityService {
    static final String SOCKET = "court-agent";
    /** Raised when a command or a reply changes in a way an older PC side cannot read. */
    static final int PROTOCOL = 1;

    private static final String TAG = "CourtAgent";
    /** The instance before this one may hold the socket name a little longer. */
    private static final int BIND_ATTEMPTS = 40;
    private static final long BIND_RETRY_MS = 50;
    /** Time a gesture may take beyond its own duration before it counts as failed. */
    private static final long GESTURE_SLACK_MS = 2000;

    private final Object changed = new Object();
    /** Accessibility events seen so far; wait_change waits for it to grow. */
    private long seq;

    private final Set<LocalSocket> clients = ConcurrentHashMap.newKeySet();
    private LocalServerSocket server;
    private boolean stopped;
    private String version = "";

    @Override
    protected void onServiceConnected() {
        try {
            version = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (Exception e) {
            Log.w(TAG, "version unknown", e);
        }
        Thread thread = new Thread(this::serve, "agent-server");
        thread.setDaemon(true);
        thread.start();
        Log.i(TAG, "connected, version " + version);
    }

    @Override
    public boolean onUnbind(Intent intent) {
        stop();
        return super.onUnbind(intent);
    }

    @Override
    public void onDestroy() {
        stop();
        super.onDestroy();
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        synchronized (changed) {
            seq++;
            changed.notifyAll();
        }
    }

    @Override
    public void onInterrupt() {
    }

    private void serve() {
        LocalServerSocket socket = bind();
        if (socket == null || !keep(socket)) {
            return;
        }
        try {
            while (true) {
                LocalSocket client = socket.accept();
                clients.add(client);
                Thread thread = new Thread(() -> handle(client), "agent-client");
                thread.setDaemon(true);
                thread.start();
            }
        } catch (IOException e) {
            Log.i(TAG, "server closed: " + e.getMessage());
        }
    }

    private LocalServerSocket bind() {
        for (int attempt = 1; attempt <= BIND_ATTEMPTS; attempt++) {
            try {
                return new LocalServerSocket(SOCKET);
            } catch (IOException e) {
                Log.w(TAG, "socket busy (attempt " + attempt + "): " + e.getMessage());
            }
            try {
                Thread.sleep(BIND_RETRY_MS);
            } catch (InterruptedException e) {
                return null;
            }
        }
        Log.e(TAG, "socket " + SOCKET + " stayed busy; not serving");
        return null;
    }

    /** Keep {@code socket} as this instance's server, unless the instance is already gone. */
    private synchronized boolean keep(LocalServerSocket socket) {
        if (stopped) {
            close(socket);
            return false;
        }
        server = socket;
        return true;
    }

    /** Free the socket name for the next instance and end every connection. */
    private synchronized void stop() {
        stopped = true;
        if (server != null) {
            close(server);
            server = null;
        }
        for (LocalSocket client : clients) {
            try {
                client.close();
            } catch (IOException ignored) {
                // closing anyway
            }
        }
        Log.i(TAG, "stopped");
    }

    private static void close(LocalServerSocket socket) {
        try {
            // Wakes the thread blocked in accept(), which would keep the name bound.
            Os.shutdown(socket.getFileDescriptor(), OsConstants.SHUT_RDWR);
        } catch (Exception ignored) {
            // the socket is closed below in any case
        }
        try {
            socket.close();
        } catch (IOException ignored) {
            // nothing more to free
        }
    }

    private void handle(LocalSocket client) {
        try (LocalSocket socket = client;
             BufferedReader in = new BufferedReader(
                     new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
             Writer out = new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8)) {
            String line;
            while ((line = in.readLine()) != null) {
                out.write(answer(line));
                out.write('\n');
                out.flush();
            }
        } catch (IOException e) {
            Log.i(TAG, "client gone: " + e.getMessage());
        } finally {
            clients.remove(client);
        }
    }

    private String answer(String line) {
        Object id = JSONObject.NULL;
        try {
            JSONObject command = new JSONObject(line);
            id = command.opt("id") == null ? JSONObject.NULL : command.opt("id");
            return run(command).put("id", id).put("ok", true).toString();
        } catch (Exception e) {
            String message = e.getMessage() == null ? e.toString() : e.getMessage();
            try {
                return new JSONObject().put("id", id).put("ok", false).put("error", message)
                        .toString();
            } catch (JSONException never) {
                return "{\"ok\":false}";
            }
        }
    }

    private JSONObject run(JSONObject command) throws Exception {
        String op = command.getString("op");
        JSONObject reply = new JSONObject();
        AccessibilityNodeInfo root;
        switch (op) {
            case "hello":
                return reply.put("protocol", PROTOCOL).put("version", version);
            case "dump":
                return reply.put("xml", Tree.dump(getRootInActiveWindow())).put("seq", seq());
            case "click": {
                root = getRootInActiveWindow();
                AccessibilityNodeInfo node = Tree.labelled(root, command.getString("label"),
                        command.getInt("x"), command.getInt("y"));
                return click(reply, node, node == null ? null : Tree.clickable(node), root);
            }
            case "click_at": {
                root = getRootInActiveWindow();
                AccessibilityNodeInfo node =
                        Tree.clickableAt(root, command.getInt("x"), command.getInt("y"));
                return click(reply, node, node, root);
            }
            case "back":
                return reply.put("done", performGlobalAction(GLOBAL_ACTION_BACK));
            case "swipe":
                return reply.put("done", swipe(command.getInt("x1"), command.getInt("y1"),
                        command.getInt("x2"), command.getInt("y2"), command.getLong("ms")));
            case "current": {
                root = getRootInActiveWindow();
                CharSequence name = root == null ? null : root.getPackageName();
                return reply.put("package", name == null ? "" : name.toString());
            }
            case "wait_change":
                return reply.put("seq",
                        waitChange(command.getLong("since"), command.optLong("timeout_ms", 0)));
            default:
                throw new IllegalArgumentException("unknown op: " + op);
        }
    }

    /** Click {@code target} for {@code found}; the reply holds the bounds of {@code found}. */
    private static JSONObject click(JSONObject reply, AccessibilityNodeInfo found,
                                    AccessibilityNodeInfo target, AccessibilityNodeInfo root)
            throws JSONException {
        if (found == null) {
            return reply.put("clicked", false);
        }
        return reply.put("clicked", target.performAction(AccessibilityNodeInfo.ACTION_CLICK))
                .put("bounds", Tree.bounds(found, root));
    }

    private long seq() {
        synchronized (changed) {
            return seq;
        }
    }

    /** Wait until an event comes after event number {@code since}; return the number then. */
    private long waitChange(long since, long timeoutMs) throws InterruptedException {
        long deadline = SystemClock.uptimeMillis() + timeoutMs;
        synchronized (changed) {
            long left = timeoutMs;
            while (seq <= since && left > 0) {
                changed.wait(left);
                left = deadline - SystemClock.uptimeMillis();
            }
            return seq;
        }
    }

    private boolean swipe(int x1, int y1, int x2, int y2, long ms) throws InterruptedException {
        Path path = new Path();
        path.moveTo(x1, y1);
        path.lineTo(x2, y2);
        GestureDescription gesture = new GestureDescription.Builder()
                .addStroke(new GestureDescription.StrokeDescription(path, 0, Math.max(1, ms)))
                .build();
        boolean[] done = {false};
        CountDownLatch finished = new CountDownLatch(1);
        boolean sent = dispatchGesture(gesture, new GestureResultCallback() {
            @Override
            public void onCompleted(GestureDescription description) {
                done[0] = true;
                finished.countDown();
            }

            @Override
            public void onCancelled(GestureDescription description) {
                finished.countDown();
            }
        }, null);
        return sent && finished.await(ms + GESTURE_SLACK_MS, TimeUnit.MILLISECONDS) && done[0];
    }
}
