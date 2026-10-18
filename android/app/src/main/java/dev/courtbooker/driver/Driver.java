package dev.courtbooker.driver;

import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.Activity;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.graphics.Rect;
import android.net.LocalServerSocket;
import android.net.LocalSocket;
import android.os.Build;
import android.os.Bundle;
import android.os.SystemClock;
import android.system.Os;
import android.system.OsConstants;
import android.util.Log;
import android.view.InputDevice;
import android.view.KeyCharacterMap;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;

/**
 * Lets the PC read and click the screen through UiAutomation, the connection uiautomator2
 * uses. Started with {@code am instrument -w dev.courtbooker.driver/.Driver}, whose
 * {@code am} process must keep running: it holds the UiAutomation connection.
 *
 * <p>Commands come as one JSON object per line on the abstract socket {@value #SOCKET}
 * (reached with {@code adb forward tcp:N localabstract:court-driver}); each gets one JSON line
 * back with the same {@code id}, {@code ok} and, when {@code ok} is false, {@code error}.
 *
 * <p>An element is clicked by its label, looked up in the tree of the moment, with an
 * accessibility click: no position travels from the PC, so a list that moved since the PC
 * read the screen cannot send the click to another element. The driver is not an
 * accessibility service and does not hide the enabled services from apps.
 */
public final class Driver extends Instrumentation {
    static final String SOCKET = "court-driver";
    /** Raised when a command or a reply changes in a way an older PC side cannot read. */
    static final int PROTOCOL = 1;

    private static final String TAG = "CourtDriver";
    private static final long SWIPE_STEP_MS = 5;

    private UiAutomation ui;
    private String version = "";
    private LocalServerSocket server;
    private LocalSocket client;
    private volatile boolean stopping;

    @Override
    public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        start();
    }

    @Override
    public void onStart() {
        try {
            version = getContext().getPackageManager()
                    .getPackageInfo(getContext().getPackageName(), 0).versionName;
        } catch (Exception e) {
            Log.w(TAG, "Version unknown", e);
        }
        ui = getUiAutomation(UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES);
        AccessibilityServiceInfo info = ui.getServiceInfo();
        // The same elements as a uiautomator2 dump, which the booking flow was written on.
        info.flags |= AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS
                | AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS;
        ui.setServiceInfo(info);
        try {
            server = new LocalServerSocket(SOCKET);
            Log.i(TAG, "Driver " + version + " serving on " + SOCKET);
            while (!stopping) {
                LocalSocket accepted = server.accept();
                replaceClient(accepted);
                Thread thread = new Thread(() -> handle(accepted), "driver-client");
                thread.setDaemon(true);
                thread.start();
            }
        } catch (IOException e) {
            if (!stopping) {
                Log.e(TAG, "Socket failed", e);
            }
        } finally {
            closeServer();
        }
        Log.i(TAG, "Stopped");
        finish(Activity.RESULT_OK, new Bundle());
    }

    /** Serve {@code accepted} from now on: a run that died must not block the next one. */
    private synchronized void replaceClient(LocalSocket accepted) {
        if (client != null) {
            close(client);
        }
        client = accepted;
    }

    private synchronized void stop() {
        stopping = true;
        closeServer();
    }

    private synchronized void closeServer() {
        if (server == null) {
            return;
        }
        try {
            // Wakes the thread blocked in accept().
            Os.shutdown(server.getFileDescriptor(), OsConstants.SHUT_RDWR);
        } catch (Exception ignored) {
            // closed below in any case
        }
        try {
            server.close();
        } catch (IOException ignored) {
            // nothing more to free
        }
        server = null;
    }

    private static void close(LocalSocket socket) {
        try {
            socket.shutdownInput();
        } catch (IOException ignored) {
            // closed below in any case
        }
        try {
            socket.close();
        } catch (IOException ignored) {
            // nothing more to free
        }
    }

    private void handle(LocalSocket socket) {
        try (BufferedReader in = new BufferedReader(
                     new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
             Writer out = new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8)) {
            String line;
            while ((line = in.readLine()) != null) {
                out.write(answer(line));
                out.write('\n');
                out.flush();
            }
        } catch (IOException e) {
            Log.i(TAG, "Client gone: " + e.getMessage());
        } finally {
            close(socket);
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
                return reply.put("protocol", PROTOCOL).put("version", version)
                        .put("sdk", Build.VERSION.SDK_INT);
            case "dump":
                return reply.put("xml", Tree.dump(ui.getRootInActiveWindow()));
            case "current": {
                root = ui.getRootInActiveWindow();
                CharSequence name = root == null ? null : root.getPackageName();
                return reply.put("package", name == null ? "" : name.toString());
            }
            case "click": {
                root = ui.getRootInActiveWindow();
                AccessibilityNodeInfo node = Tree.labelled(root, command.getString("label"),
                        command.getInt("x"), command.getInt("y"));
                return click(node, root, reply);
            }
            case "click_at": {
                root = ui.getRootInActiveWindow();
                AccessibilityNodeInfo node = Tree.clickableAt(root, command.getInt("x"),
                        command.getInt("y"));
                return click(node, root, reply);
            }
            case "back":
                key(KeyEvent.KEYCODE_BACK);
                return reply;
            case "swipe":
                swipe(command.getInt("x1"), command.getInt("y1"), command.getInt("x2"),
                        command.getInt("y2"), command.getLong("ms"));
                return reply;
            case "stop":
                stop();
                return reply;
            default:
                throw new IllegalArgumentException("unknown op: " + op);
        }
    }

    /**
     * Click {@code node} where it is now: an accessibility click when it is clickable, else a
     * touch on its middle. No node gives {@code clicked: false}: whatever is at its old place
     * now is another element, and the PC reads the screen and clicks again if it has to.
     */
    private JSONObject click(AccessibilityNodeInfo node, AccessibilityNodeInfo root,
            JSONObject reply) throws JSONException {
        if (node == null) {
            return reply.put("clicked", false);
        }
        Rect r = Tree.rect(node, root);
        String how = "action";
        if (!node.isClickable() || !node.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
            tap(r.centerX(), r.centerY());
            how = "touch";
        }
        return reply.put("clicked", true).put("how", how).put("bounds", Tree.format(r));
    }

    /** Tap (x, y) with a bare touch down and up, like a finger. */
    private void tap(int x, int y) {
        long down = SystemClock.uptimeMillis();
        touch(MotionEvent.ACTION_DOWN, down, down, x, y);
        touch(MotionEvent.ACTION_UP, down, SystemClock.uptimeMillis(), x, y);
    }

    private void swipe(int x1, int y1, int x2, int y2, long ms) throws InterruptedException {
        long steps = Math.max(1, ms / SWIPE_STEP_MS);
        long down = SystemClock.uptimeMillis();
        touch(MotionEvent.ACTION_DOWN, down, down, x1, y1);
        for (long i = 1; i <= steps; i++) {
            Thread.sleep(SWIPE_STEP_MS);
            float x = x1 + (x2 - x1) * i / (float) steps;
            float y = y1 + (y2 - y1) * i / (float) steps;
            touch(MotionEvent.ACTION_MOVE, down, SystemClock.uptimeMillis(), x, y);
        }
        touch(MotionEvent.ACTION_UP, down, SystemClock.uptimeMillis(), x2, y2);
    }

    private void touch(int action, long downTime, long eventTime, float x, float y) {
        MotionEvent.PointerProperties finger = new MotionEvent.PointerProperties();
        finger.id = 0;
        finger.toolType = MotionEvent.TOOL_TYPE_FINGER;
        MotionEvent.PointerCoords at = new MotionEvent.PointerCoords();
        at.x = x;
        at.y = y;
        at.pressure = 1;
        at.size = 1;
        MotionEvent event = MotionEvent.obtain(downTime, eventTime, action, 1,
                new MotionEvent.PointerProperties[] {finger}, new MotionEvent.PointerCoords[] {at},
                0, 0, 1, 1, 0, 0, InputDevice.SOURCE_TOUCHSCREEN, 0);
        try {
            if (!ui.injectInputEvent(event, true)) {
                throw new IllegalStateException("Android refused the touch");
            }
        } finally {
            event.recycle();
        }
    }

    private void key(int code) {
        long now = SystemClock.uptimeMillis();
        KeyEvent down = new KeyEvent(now, now, KeyEvent.ACTION_DOWN, code, 0, 0,
                KeyCharacterMap.VIRTUAL_KEYBOARD, 0, 0, InputDevice.SOURCE_KEYBOARD);
        if (!ui.injectInputEvent(down, true)
                || !ui.injectInputEvent(KeyEvent.changeAction(down, KeyEvent.ACTION_UP), true)) {
            throw new IllegalStateException("Android refused the key");
        }
    }
}
