import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fakeConnection, step } from "../test/liveSocket";
import {
  connectLiveFeed,
  type LiveState,
  liveUrl,
  OPEN_TIMEOUT_MS,
  RECONNECT_DELAYS_MS,
  stepOf,
} from "./live";
import type { Step } from "./types";

/** A feed message carrying `value` as the step. */
function message(value: unknown): string {
  return JSON.stringify({ type: "step", step: value });
}

/** Connect a feed to fake sockets and record what it reports. */
function connect() {
  const { connection, sockets, current } = fakeConnection();
  const steps: Step[] = [];
  const states: LiveState[] = [];
  const stop = connectLiveFeed({
    ...connection,
    onStep: (received) => steps.push(received),
    onState: (state) => states.push(state),
  });
  return { sockets, steps, states, stop, current };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("connectLiveFeed", () => {
  it("passes each step on in order once the socket is open", () => {
    const feed = connect();

    feed.current().open();
    feed.current().send(step(1));
    feed.current().send(step(2));

    expect(feed.states).toEqual(["connecting", "open"]);
    expect(feed.steps.map(({ id }) => id)).toEqual([1, 2]);
    expect(feed.current().url).toBe("live");
  });

  it("reconnects after a drop and resumes after the last step seen", () => {
    const feed = connect();
    feed.current().open();
    feed.current().send(step(7));

    feed.current().drop();
    expect(feed.states.at(-1)).toBe("closed");
    vi.advanceTimersByTime(RECONNECT_DELAYS_MS[0] - 1);
    expect(feed.sockets).toHaveLength(1);
    vi.advanceTimersByTime(1);

    expect(feed.sockets).toHaveLength(2);
    expect(feed.current().url).toBe("live?after=7");
  });

  it("waits longer after each failed attempt, then keeps the longest wait", () => {
    const feed = connect();
    const waits: number[] = [];

    for (let attempt = 0; attempt < RECONNECT_DELAYS_MS.length + 1; attempt += 1) {
      const before = feed.sockets.length;
      feed.current().drop();
      let waited = 0;
      while (feed.sockets.length === before) {
        vi.advanceTimersByTime(100);
        waited += 100;
      }
      waits.push(waited);
    }

    expect(waits).toEqual([...RECONNECT_DELAYS_MS, RECONNECT_DELAYS_MS.at(-1)]);
  });

  it("starts over with the shortest wait once a connection opens", () => {
    const feed = connect();
    feed.current().drop();
    vi.advanceTimersByTime(RECONNECT_DELAYS_MS[0]);
    feed.current().drop();
    vi.advanceTimersByTime(RECONNECT_DELAYS_MS[1]);

    feed.current().open();
    feed.current().drop();
    vi.advanceTimersByTime(RECONNECT_DELAYS_MS[0]);

    expect(feed.sockets).toHaveLength(4);
  });

  it("gives up on a socket that does not open in time and tries again", () => {
    const feed = connect();

    vi.advanceTimersByTime(OPEN_TIMEOUT_MS);
    expect(feed.sockets[0]?.closed).toBe(true);
    expect(feed.states.at(-1)).toBe("closed");
    vi.advanceTimersByTime(RECONNECT_DELAYS_MS[0]);

    expect(feed.sockets).toHaveLength(2);
  });

  it("tries again even when the stuck socket never reports its close", () => {
    const feed = connect();
    const stuck = feed.current();
    stuck.close = () => {
      stuck.closed = true;
    };

    vi.advanceTimersByTime(OPEN_TIMEOUT_MS + RECONNECT_DELAYS_MS[0]);

    expect(stuck.closed).toBe(true);
    expect(feed.sockets).toHaveLength(2);
  });

  it("ignores a late close of a socket it already gave up on", () => {
    const feed = connect();
    const stuck = feed.current();
    vi.advanceTimersByTime(OPEN_TIMEOUT_MS + RECONNECT_DELAYS_MS[0]);
    feed.current().open();

    stuck.drop();
    vi.advanceTimersByTime(60_000);

    expect(feed.sockets).toHaveLength(2);
    expect(feed.states.at(-1)).toBe("open");
  });

  it("never closes an open socket for being slow", () => {
    const feed = connect();
    feed.current().open();

    vi.advanceTimersByTime(OPEN_TIMEOUT_MS * 10);

    expect(feed.current().closed).toBe(false);
    expect(feed.sockets).toHaveLength(1);
  });

  it("does not pass a step on twice", () => {
    const feed = connect();
    feed.current().open();

    feed.current().send(step(3));
    feed.current().send(step(3));
    feed.current().send(step(2));

    expect(feed.steps.map(({ id }) => id)).toEqual([3]);
  });

  it("closes the socket on stop and never reconnects", () => {
    const feed = connect();
    feed.current().open();

    feed.stop();
    vi.advanceTimersByTime(60_000);

    expect(feed.current().closed).toBe(true);
    expect(feed.sockets).toHaveLength(1);
    expect(feed.states.at(-1)).toBe("open");
  });

  it("cancels a pending reconnect on stop", () => {
    const feed = connect();
    feed.current().drop();

    feed.stop();
    vi.advanceTimersByTime(60_000);

    expect(feed.sockets).toHaveLength(1);
  });
});

describe("stepOf", () => {
  it("reads a step message", () => {
    expect(stepOf(message(step(1)))).toEqual(step(1));
  });

  it.each([
    ["text that is not JSON", "not json"],
    ["a message of another type", JSON.stringify({ type: "ping" })],
    ["a step without an id", message({ kind: "x", category: "step", time: "06:00" })],
    ["a step that is not an object", message("step")],
    ["binary data", new ArrayBuffer(4)],
  ])("ignores %s", (_name, data) => {
    expect(stepOf(data)).toBeNull();
  });
});

describe("liveUrl", () => {
  it("points at this page's host, resuming after a step when given", () => {
    expect(liveUrl(null)).toBe(`ws://${window.location.host}/api/live`);
    expect(liveUrl(42)).toBe(`ws://${window.location.host}/api/live?after=42`);
  });
});
