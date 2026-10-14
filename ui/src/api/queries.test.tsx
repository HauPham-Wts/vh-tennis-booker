import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { reply, requestsTo, stubBackend } from "../test/backend";
import { createTestQueryClient, withQueryClient } from "../test/queries";
import { ApiError } from "./client";
import { useOverview, useRuns } from "./queries";
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

  it("keep each History filter apart in the cache", async () => {
    const fetch = stubBackend({ "GET /api/runs": reply([]) });
    const wrapper = withQueryClient(createTestQueryClient());

    const october = renderHook(() => useRuns({ month: "2026-10" }), { wrapper });
    const dryRuns = renderHook(() => useRuns({ trigger: "dry_run" }), { wrapper });

    await waitFor(() => expect(october.result.current.isSuccess).toBe(true));
    await waitFor(() => expect(dryRuns.result.current.isSuccess).toBe(true));
    expect(requestsTo(fetch, "GET /api/runs")).toBe(2);
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
