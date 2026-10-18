package dev.courtbooker.agent;

import android.graphics.Rect;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.ArrayDeque;

/**
 * Reads the accessibility tree the way the uiautomator2 dump does: only nodes visible to the
 * user, bounds clipped to the screen, the label in {@code content-desc}.
 */
final class Tree {
    private Tree() {
    }

    /** Return the tree under {@code root} as uiautomator2-style XML; no root gives none. */
    static String dump(AccessibilityNodeInfo root) {
        if (root == null) {
            return "<hierarchy/>";
        }
        StringBuilder xml = new StringBuilder("<hierarchy>");
        dump(root, screen(root), xml);
        return xml.append("</hierarchy>").toString();
    }

    /**
     * Return the visible node labelled {@code label} whose bounds hold (x, y), else the one
     * whose centre is nearest to it; null when no visible node has that label.
     */
    static AccessibilityNodeInfo labelled(AccessibilityNodeInfo root, String label, int x, int y) {
        if (root == null) {
            return null;
        }
        Rect screen = screen(root);
        AccessibilityNodeInfo best = null;
        long bestDistance = Long.MAX_VALUE;
        for (AccessibilityNodeInfo node : visible(root)) {
            if (!label.contentEquals(text(node.getContentDescription()))) {
                continue;
            }
            Rect r = bounds(node, screen);
            if (r.contains(x, y)) {
                return node;
            }
            long dx = r.centerX() - x;
            long dy = r.centerY() - y;
            if (dx * dx + dy * dy < bestDistance) {
                best = node;
                bestDistance = dx * dx + dy * dy;
            }
        }
        return best;
    }

    /** Return the smallest visible clickable node holding (x, y), as a tap there would hit. */
    static AccessibilityNodeInfo clickableAt(AccessibilityNodeInfo root, int x, int y) {
        if (root == null) {
            return null;
        }
        Rect screen = screen(root);
        AccessibilityNodeInfo best = null;
        long bestArea = Long.MAX_VALUE;
        for (AccessibilityNodeInfo node : visible(root)) {
            Rect r = bounds(node, screen);
            long area = (long) r.width() * r.height();
            if (node.isClickable() && r.contains(x, y) && area < bestArea) {
                best = node;
                bestArea = area;
            }
        }
        return best;
    }

    /** Return {@code node} if it is clickable, else its nearest clickable ancestor. */
    static AccessibilityNodeInfo clickable(AccessibilityNodeInfo node) {
        for (AccessibilityNodeInfo current = node; current != null; current = current.getParent()) {
            if (current.isClickable()) {
                return current;
            }
        }
        return node;
    }

    /** Return the bounds of {@code node} on the screen as "[left,top][right,bottom]". */
    static String bounds(AccessibilityNodeInfo node, AccessibilityNodeInfo root) {
        Rect r = bounds(node, screen(root));
        return "[" + r.left + "," + r.top + "][" + r.right + "," + r.bottom + "]";
    }

    private static Rect screen(AccessibilityNodeInfo root) {
        Rect r = new Rect();
        root.getBoundsInScreen(r);
        return r;
    }

    private static Rect bounds(AccessibilityNodeInfo node, Rect screen) {
        Rect r = new Rect();
        node.getBoundsInScreen(r);
        if (!r.intersect(screen)) {
            r.setEmpty();
        }
        return r;
    }

    /** Return the root and every node below it that is visible, parents before children. */
    private static Iterable<AccessibilityNodeInfo> visible(AccessibilityNodeInfo root) {
        ArrayDeque<AccessibilityNodeInfo> found = new ArrayDeque<>();
        ArrayDeque<AccessibilityNodeInfo> queue = new ArrayDeque<>();
        queue.add(root);
        while (!queue.isEmpty()) {
            AccessibilityNodeInfo node = queue.removeFirst();
            found.addLast(node);
            for (int i = 0; i < node.getChildCount(); i++) {
                AccessibilityNodeInfo child = node.getChild(i);
                if (child != null && child.isVisibleToUser()) {
                    queue.addLast(child);
                }
            }
        }
        return found;
    }

    private static void dump(AccessibilityNodeInfo node, Rect screen, StringBuilder xml) {
        Rect r = bounds(node, screen);
        xml.append("<node text=\"").append(escape(node.getText()))
                .append("\" class=\"").append(escape(node.getClassName()))
                .append("\" content-desc=\"").append(escape(node.getContentDescription()))
                .append("\" clickable=\"").append(node.isClickable())
                .append("\" enabled=\"").append(node.isEnabled())
                .append("\" bounds=\"[").append(r.left).append(',').append(r.top)
                .append("][").append(r.right).append(',').append(r.bottom).append("]\">");
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child != null && child.isVisibleToUser()) {
                dump(child, screen, xml);
            }
        }
        xml.append("</node>");
    }

    private static CharSequence text(CharSequence value) {
        return value == null ? "" : value;
    }

    private static String escape(CharSequence value) {
        if (value == null) {
            return "";
        }
        StringBuilder out = new StringBuilder(value.length());
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '&': out.append("&amp;"); break;
                case '<': out.append("&lt;"); break;
                case '>': out.append("&gt;"); break;
                case '"': out.append("&quot;"); break;
                case '\n': out.append("&#10;"); break;
                case '\r': out.append("&#13;"); break;
                case '\t': out.append("&#9;"); break;
                default:
                    // XML 1.0 cannot hold other control characters; drop them.
                    if (c >= 0x20) {
                        out.append(c);
                    }
            }
        }
        return out.toString();
    }
}
