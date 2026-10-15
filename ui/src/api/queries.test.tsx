import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { reply, requestsTo, stubBackend } from "../test/backend";
import { createTestQueryClient, withQueryClient } from "../test/queries";
import { ApiError } from "./client";
import {
  SETTLING_POLL_MS,
  settlingInterval,
  useOverview,
  useRunMonths,
  useRuns,
  useSetupChecks,
} from "./queries";
import type { Overview } from "./types";
import { createQueryClient, shouldRetry, UNREACHABLE_RETRIES } from "./queryClient";

const unreachable = new ApiError(0, { error: "unreachable", detail: "fetch failed" });
const lockHeld = new ApiError(409, { error: "lock_held", detail: "Another run is in progress" });

describe("shouldRetry", () => {
  it("retries a read while no backend answers, a few times", () => {
    expect(shouldRetry(0, unreachable)).toBe(true);
    expect(shouldRetry(UNREACHABLE_RETRIES - 1, unreachable)).toBe(true);
    expect(shouldRetry(UNREACHABLE_RETRIES, unreachable)).toBe(false);
  });

  it("does not retry a Problem the backend sent, or an error of the UI", () => {
    expect(shouldRetry(0, lockHeld)).toBe(false);
    expect(shouldRetry(0, new TypeError("x is undefined"))).toBe(false);
  });
});

describe("createQueryClient", () => {
  it("keeps a read fresh, yet reads it again at once when a step marks it stale", async () => {
    const fetch = stubBackend({ "GET /api/status": reply({ version: "0.6.0" }) });
    const client = createQueryClient();
    const wrapper = withQueryClient(client);
    const first = renderHook(() => useOverview(), { wrapper });
    await waitFor(() => expect(first.result.current.isSuccess).toBe(true));

    // A second screen showing the same data within the fresh time reads nothing.
    const second = renderHook(() => useOverview(), { wrapper });
    expect(second.result.current.isSuccess).toBe(true);
    expect(requestsTo(fetch, "GET /api/status")).toBe(1);

    await client.invalidateQueries({ queryKey: ["overview"] });

    expect(requestsTo(fetch, "GET /api/status")).toBe(2);
  });
});

describe("settlingInterval", () => {
  const base = { running: null, last_run: null } as unknown as Overview;
  const holding = (trigger: string, lastStatus?: string) =>
    ({
      ...base,
      running: { trigger, pid: 1, since: "05:50:02" },
      last_run: lastStatus === undefined ? null : { id: 30, status: lastStatus },
    }) as unknown as Overview;

  it("reads nothing again while nothing runs or a booking goes on", () => {
    expect(settlingInterval(undefined)).toBe(false);
    expect(settlingInterval(base)).toBe(false);
    expect(settlingInterval(holding("scheduled", "running"))).toBe(false);
    expect(settlingInterval(holding("dry_run", "running"))).toBe(false);
  });

  it("reads every 2 s while a run is starting or letting go, and during auto setup", () => {
    expect(settlingInterval(holding("dry_run"))).toBe(SETTLING_POLL_MS);
    expect(settlingInterval(holding("scheduled", "ok"))).toBe(SETTLING_POLL_MS);
    expect(settlingInterval(holding("setup", "ok"))).toBe(SETTLING_POLL_MS);
  });
});

describe("query hooks", () => {
  it("read the overview", async () => {
    const overview = { version: "0.6.0", running: null, last_run: null, setup: null };
    stubBackend({ "GET /api/status": reply(overview) });

    const { result } = renderHook(() => useOverview(), {
      wrapper: withQueryClient(createTestQueryClient()),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(overview);
  });

  it("read the months of real bookings", async () => {
    const months = [{ month: "2026-10", runs: 5, booked: 10 }];
    stubBackend({ "GET /api/runs/months": reply(months) });

    const { result } = renderHook(() => useRunMonths(), {
      wrapper: withQueryClient(createTestQueryClient()),
    });

    await waitFor(() => expect(result.current.data).toEqual(months));
  });

  it("keep each History filter apart in the cache", async () => {
    const fetch = stubBackend({ "GET /api/runs": reply([]) });
    const wrapper = withQueryClient(createTestQueryClient());

    const october = renderHook(() => useRuns({ month: "2026-10" }), { wrapper });
    const dryRuns = renderHook(() => useRuns({ trigger: "dry_run" }), { wrapper });

    await waitFor(() => expect(october.result.current.isSuccess).toBe(true));
    await waitFor(() => expect(dryRuns.result.current.isSuccess).toBe(true));
    expect(requestsTo(fetch, "GET /api/runs")).toBe(2);
  });

  it("read the setup checks only when allowed, as no run holds the lock", async () => {
    const fetch = stubBackend({ "GET /api/setup": reply([]) });
    const wrapper = withQueryClient(createTestQueryClient());

    const { result, rerender } = renderHook(({ enabled }) => useSetupChecks(enabled), {
      wrapper,
      initialProps: { enabled: false },
    });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(requestsTo(fetch, "GET /api/setup")).toBe(0);

    rerender({ enabled: true });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(requestsTo(fetch, "GET /api/setup")).toBe(1);
  });

  it("report a Problem as an ApiError without retrying", async () => {
    const fetch = stubBackend({
      "GET /api/status": reply({ error: "engine", detail: "database is locked" }, 500),
    });

    const { result } = renderHook(() => useOverview(), {
      wrapper: withQueryClient(createTestQueryClient()),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect((result.current.error as ApiError).code).toBe("engine");
    expect(requestsTo(fetch, "GET /api/status")).toBe(1);
  });
});
