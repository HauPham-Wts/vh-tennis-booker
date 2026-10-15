import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, renderHook, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { fakeConnection, step } from "../test/liveSocket";
import { createTestQueryClient } from "../test/queries";
import { MAX_LIVE_STEPS, staleKeysFor, useLiveFeed } from "./liveContext";
import { LiveProvider } from "./LiveProvider";
import { queryKeys } from "./queries";

/** Show the feed as a screen would: its state and the ids of its steps. */
function FeedProbe() {
  const { state, steps } = useLiveFeed();
  return (
    <p>
      {state}: {steps.map(({ id }) => id).join(",")}
    </p>
  );
}

/** Render the provider on fake sockets with its own cache. */
function renderFeed() {
  const fake = fakeConnection();
  const cache = createTestQueryClient();
  const view = render(
    <QueryClientProvider client={cache}>
      <LiveProvider connection={fake.connection}>
        <FeedProbe />
      </LiveProvider>
    </QueryClientProvider>,
  );
  return { ...fake, cache, view };
}

describe("LiveProvider", () => {
  it("shows the connection state and each new step", () => {
    const feed = renderFeed();
    expect(screen.getByText(/^connecting/)).toBeInTheDocument();

    act(() => {
      feed.current().open();
      feed.current().send(step(1));
      feed.current().send(step(2));
    });

    expect(screen.getByText("open: 1,2")).toBeInTheDocument();
  });

  it("keeps only the most recent steps", () => {
    const feed = renderFeed();

    act(() => {
      feed.current().open();
      for (let id = 1; id <= MAX_LIVE_STEPS + 5; id += 1) {
        feed.current().send(step(id));
      }
    });

    const ids = screen.getByText(/^open/).textContent?.replace("open: ", "").split(",") ?? [];
    expect(ids).toHaveLength(MAX_LIVE_STEPS);
    expect(ids[0]).toBe("6");
  });

  it("marks the data a step changes as stale", () => {
    const feed = renderFeed();
    const invalidate = vi.spyOn(feed.cache, "invalidateQueries");

    act(() => {
      feed.current().open();
      feed.current().send(step(9, { run_id: 3, kind: "slot_booked", category: "slot" }));
    });

    const keys = invalidate.mock.calls.map(([filters]) => filters?.queryKey);
    expect(keys).toEqual([queryKeys.overview, ["runs"]]);
  });

  it("sends no request for the ordinary steps of a run", () => {
    const feed = renderFeed();
    const invalidate = vi.spyOn(feed.cache, "invalidateQueries");

    act(() => {
      feed.current().open();
      for (const kind of ["calendar_opened", "date_selected", "slot_selected"] as const) {
        feed.current().send(step(10, { run_id: 3, kind }));
      }
    });

    expect(invalidate).not.toHaveBeenCalled();
  });

  it("closes the connection when the app goes away", () => {
    const feed = renderFeed();

    feed.view.unmount();

    expect(feed.current().closed).toBe(true);
  });
});

describe("useLiveFeed", () => {
  it("needs a LiveProvider", () => {
    // React reports the thrown error on the console; the throw is what matters.
    vi.spyOn(console, "error").mockImplementation(() => undefined);

    expect(() => renderHook(() => useLiveFeed())).toThrow("needs a LiveProvider");
  });
});

describe("staleKeysFor", () => {
  it("leaves the steps inside a run to the live feed", () => {
    for (const kind of ["device_ready", "waiting", "booking_started", "court_selected"] as const) {
      expect(staleKeysFor(step(1, { run_id: 3, kind })), kind).toEqual([]);
    }
  });

  it("refreshes the overview and the runs when a run starts or a slot ends", () => {
    for (const kind of ["run_started", "slot_booked", "slot_failed"] as const) {
      expect(staleKeysFor(step(1, { run_id: 3, kind })), kind).toEqual([
        queryKeys.overview,
        ["runs"],
      ]);
    }
  });

  it("also refreshes the run itself and the schedule when it ends", () => {
    // The final log, and dry_run_passed for the schedule switch.
    expect(staleKeysFor(step(1, { run_id: 3, kind: "run_finished" }))).toEqual([
      queryKeys.overview,
      ["runs"],
      queryKeys.run(3),
      queryKeys.schedule,
    ]);
  });

  it("makes a settings step stale the settings and the schedule", () => {
    expect(
      staleKeysFor(step(1, { run_id: null, kind: "settings_saved", category: "settings" })),
    ).toEqual([queryKeys.overview, queryKeys.settings, queryKeys.schedule]);
  });

  it("makes a setup step stale the setup checks", () => {
    expect(
      staleKeysFor(step(1, { run_id: null, kind: "setup_finished", category: "setup" })),
    ).toEqual([queryKeys.overview, queryKeys.setup]);
  });

  it("makes a schedule step stale the schedule", () => {
    expect(
      staleKeysFor(step(1, { run_id: null, kind: "schedule_enabled", category: "schedule" })),
    ).toEqual([queryKeys.overview, queryKeys.schedule]);
  });
});
