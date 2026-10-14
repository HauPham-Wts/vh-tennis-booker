import type { LiveFeedOptions, LiveSocket } from "../api/live";
import type { Step } from "../api/types";

/** A WebSocket the test drives: open it, send it messages, drop it. */
export class FakeSocket implements LiveSocket {
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  closed = false;
  readonly url: string;

  constructor(url: string) {
    this.url = url;
  }

  open(): void {
    this.onopen?.(new Event("open"));
  }

  receive(data: unknown): void {
    this.onmessage?.(new MessageEvent("message", { data }));
  }

  /** Send `step` as the backend's feed message. */
  send(step: Step): void {
    this.receive(JSON.stringify({ type: "step", step }));
  }

  drop(): void {
    this.onclose?.(new CloseEvent("close"));
  }

  close(): void {
    this.closed = true;
    this.drop();
  }
}

/** A step of the activity log, with `id` and anything else given. */
export function step(id: number, fields: Partial<Step> = {}): Step {
  return {
    id,
    run_id: 1,
    time: "2026-10-15T06:00:00",
    category: "step",
    kind: "slot_started",
    data: {},
    ...fields,
  };
}

/** A live feed connection to fake sockets; `current()` is the newest socket. */
export function fakeConnection() {
  const sockets: FakeSocket[] = [];
  const connection: Pick<LiveFeedOptions, "url" | "createSocket"> = {
    url: (after) => (after === null ? "live" : `live?after=${after}`),
    createSocket: (url) => {
      const socket = new FakeSocket(url);
      sockets.push(socket);
      return socket;
    },
  };
  const current = (): FakeSocket => {
    const socket = sockets.at(-1);
    if (socket === undefined) {
      throw new Error("No socket was opened");
    }
    return socket;
  };
  return { connection, sockets, current };
}
