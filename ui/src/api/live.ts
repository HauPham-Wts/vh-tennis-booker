/**
 * The live feed (`WS /api/live`): each new activity log step as `{"type": "step", "step"}`.
 * WebSockets are not in the OpenAPI schema, so the message is checked here.
 */
import type { Step } from "./types";

/** `connecting` until the socket opens; `closed` while waiting to reconnect. */
export type LiveState = "connecting" | "open" | "closed";

/** The part of a WebSocket the feed uses; tests stand in for it. */
export interface LiveSocket {
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  close(): void;
}

/** Waits before each reconnect; the last one repeats until the backend is back. */
export const RECONNECT_DELAYS_MS = [500, 1000, 2000, 5000] as const;

/**
 * A socket not open by then is closed and tried again. Vite's proxy, with no backend behind
 * it, accepts the socket and then neither opens nor closes it.
 */
export const OPEN_TIMEOUT_MS = 5000;

export interface LiveFeedOptions {
  /** Receives each new step once, oldest first. */
  onStep: (step: Step) => void;
  onState?: (state: LiveState) => void;
  /** The feed's address; `after` resumes after that step. Defaults to this page's host. */
  url?: (after: number | null) => string;
  createSocket?: (url: string) => LiveSocket;
}

/** Return the feed's address on this page's host, resuming after step `after`. */
export function liveUrl(after: number | null): string {
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const query = after === null ? "" : `?after=${after}`;
  return `${scheme}://${window.location.host}/api/live${query}`;
}

/** Return the step of a feed message, or null for anything else. */
export function stepOf(data: unknown): Step | null {
  if (typeof data !== "string") {
    return null;
  }
  let message: unknown;
  try {
    message = JSON.parse(data);
  } catch {
    return null;
  }
  if (typeof message !== "object" || message === null) {
    return null;
  }
  const { type, step } = message as Record<string, unknown>;
  if (type !== "step" || typeof step !== "object" || step === null) {
    return null;
  }
  const { id, kind, category, time } = step as Record<string, unknown>;
  const valid =
    typeof id === "number" &&
    typeof kind === "string" &&
    typeof category === "string" &&
    typeof time === "string";
  return valid ? (step as Step) : null;
}

/**
 * Keep a connection to the live feed: pass each new step on, reconnect after a drop and
 * resume after the last step seen, so none is missed or repeated. Returns `stop`.
 */
export function connectLiveFeed({
  onStep,
  onState = () => undefined,
  url = liveUrl,
  createSocket = (address) => new WebSocket(address),
}: LiveFeedOptions): () => void {
  let socket: LiveSocket | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let lastId: number | null = null;
  let failures = 0;
  let stopped = false;

  /** Reconnect after `current` dropped; a socket already replaced or stopped is ignored. */
  function dropped(current: LiveSocket): void {
    if (stopped || socket !== current) {
      return;
    }
    socket = null;
    onState("closed");
    const delay = RECONNECT_DELAYS_MS[Math.min(failures, RECONNECT_DELAYS_MS.length - 1)] ?? 5000;
    failures += 1;
    timer = setTimeout(open, delay);
  }

  function open(): void {
    onState("connecting");
    const current = createSocket(url(lastId));
    socket = current;
    // Retry at once: a socket closed before it opened may never report its close (Node).
    const openTimer = setTimeout(() => {
      dropped(current);
      current.close();
    }, OPEN_TIMEOUT_MS);
    current.onopen = () => {
      clearTimeout(openTimer);
      failures = 0;
      onState("open");
    };
    current.onmessage = (event) => {
      const step = stepOf(event.data);
      // The backend sends steps in id order; an older id would be a repeat.
      if (step !== null && (lastId === null || step.id > lastId)) {
        lastId = step.id;
        onStep(step);
      }
    };
    current.onclose = () => {
      clearTimeout(openTimer);
      dropped(current);
    };
  }

  open();
  return () => {
    stopped = true;
    if (timer !== null) {
      clearTimeout(timer);
    }
    socket?.close();
  };
}
