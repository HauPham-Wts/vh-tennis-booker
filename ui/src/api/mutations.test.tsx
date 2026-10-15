import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { reply, requestsTo, stubBackend } from "../test/backend";
import { createTestQueryClient, withQueryClient } from "../test/queries";
import { ApiError } from "./client";
import { useSaveSettings, useStartDryRun, useSwitchSchedule } from "./mutations";
import { queryKeys, useOverview } from "./queries";
import type { ScheduleState, Settings } from "./types";

const overview = { version: "0.6.0", running: null, last_run: null, setup: null };
const settings = { slots: ["18:00 - 19:00", "19:00 - 20:00"], court: "S10" } as Settings;
const schedule = { enabled: true, wake_at: "05:50", start_at: "06:00" } as ScheduleState;

/** Render a mutation hook beside the overview query, sharing one cache. */
function renderWithOverview<T>(useMutationHook: () => T) {
  const cache = createTestQueryClient();
  const wrapper = withQueryClient(cache);
  const overviewHook = renderHook(() => useOverview(), { wrapper });
  const mutationHook = renderHook(useMutationHook, { wrapper });
  return { cache, overviewHook, mutationHook };
}

describe("mutation hooks", () => {
  it("save the settings, cache the answer and refresh the overview", async () => {
    const fetch = stubBackend({
      "GET /api/status": reply(overview),
      "PUT /api/settings": reply(settings),
    });
    const { cache, overviewHook, mutationHook } = renderWithOverview(() => useSaveSettings());
    await waitFor(() => expect(overviewHook.result.current.isSuccess).toBe(true));

    await act(() => mutationHook.result.current.mutateAsync(settings));

    expect(cache.getQueryData(queryKeys.settings)).toEqual(settings);
    await waitFor(() => expect(requestsTo(fetch, "GET /api/status")).toBe(2));
  });

  it("switch the schedule and cache its new state", async () => {
    const fetch = stubBackend({
      "GET /api/status": reply(overview),
      "PUT /api/schedule": reply(schedule),
    });
    const { cache, mutationHook } = renderWithOverview(() => useSwitchSchedule());

    await act(() => mutationHook.result.current.mutateAsync(true));

    expect(cache.getQueryData(queryKeys.schedule)).toEqual(schedule);
    const put = fetch.mock.calls.map(([request]) => request).find((r) => r.method === "PUT");
    expect(await put?.json()).toEqual({ enabled: true });
  });

  it("leave the cache alone when the backend refuses", async () => {
    stubBackend({
      "GET /api/status": reply(overview),
      "PUT /api/schedule": reply({ error: "dry_run_required", detail: "No dry run passed" }, 409),
    });
    const { cache, mutationHook } = renderWithOverview(() => useSwitchSchedule());

    await act(async () => {
      await expect(mutationHook.result.current.mutateAsync(true)).rejects.toBeInstanceOf(ApiError);
    });

    await waitFor(() => expect(mutationHook.result.current.isError).toBe(true));
    expect((mutationHook.result.current.error as ApiError).code).toBe("dry_run_required");
    expect(cache.getQueryData(queryKeys.schedule)).toBeUndefined();
  });

  it("start a dry run once and refresh the overview to show it", async () => {
    const fetch = stubBackend({
      "GET /api/status": reply(overview),
      "POST /api/runs/dry-run": reply({ pid: 4242, started_at: "2026-10-14T13:30:00" }, 202),
    });
    const { overviewHook, mutationHook } = renderWithOverview(() => useStartDryRun());
    await waitFor(() => expect(overviewHook.result.current.isSuccess).toBe(true));

    await act(() => mutationHook.result.current.mutateAsync());

    expect(requestsTo(fetch, "POST /api/runs/dry-run")).toBe(1);
    await waitFor(() => expect(requestsTo(fetch, "GET /api/status")).toBe(2));
  });
});
