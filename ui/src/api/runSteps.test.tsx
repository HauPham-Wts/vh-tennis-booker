import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { reply, requestsTo, stubBackend } from "../test/backend";
import { fakeConnection, step } from "../test/liveSocket";
import { createTestQueryClient } from "../test/queries";
import { LiveProvider } from "./LiveProvider";
import { useRunSteps } from "./runSteps";

/** A running run as GET /api/runs/3 gives it, with its first two steps. */
const RUN = {
  id: 3,
  trigger: "dry_run",
  dry_run: true,
  version: "0.6.0",
  started_at: "2026-10-15T10:00:00.000",
  finished_at: null,
  play_date: "2026-10-17",
  court: "S6 - Sân tennis",
  status: "running",
  error: null,
  booked: 0,
  total: 0,
  slots: [],
  steps: [step(1, { run_id: 3, kind: "run_started" }), step(2, { run_id: 3, kind: "app_ready" })],
  log_lines: [],
};

function renderRunSteps() {
  const fetch = stubBackend({ "GET /api/runs/3": reply(RUN) });
  const fake = fakeConnection();
  const cache = createTestQueryClient();
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={cache}>
      <LiveProvider connection={fake.connection}>{children}</LiveProvider>
    </QueryClientProvider>
  );
  const hook = renderHook(() => useRunSteps(3), { wrapper });
  return { ...hook, ...fake, fetch };
}

const ids = (steps: readonly { id: number }[]) => steps.map(({ id }) => id);

describe("useRunSteps", () => {
  it("adds the steps the live feed brings after the stored ones, without a request", async () => {
    const { result, current, fetch } = renderRunSteps();
    await waitFor(() => expect(ids(result.current.steps)).toEqual([1, 2]));

    act(() => {
      current().open();
      current().send(step(3, { run_id: 3, kind: "booking_started" }));
      current().send(step(4, { run_id: 9, kind: "app_ready" }));
      current().send(step(5, { run_id: 3, kind: "slot_started" }));
    });

    expect(ids(result.current.steps)).toEqual([1, 2, 3, 5]);
    expect(requestsTo(fetch, "GET /api/runs/3")).toBe(1);
  });

  it("does not repeat a step the read already had", async () => {
    const { result, current } = renderRunSteps();

    act(() => {
      current().open();
      current().send(step(2, { run_id: 3, kind: "app_ready" }));
    });
    await waitFor(() => expect(result.current.run.isSuccess).toBe(true));

    expect(ids(result.current.steps)).toEqual([1, 2]);
  });
});
