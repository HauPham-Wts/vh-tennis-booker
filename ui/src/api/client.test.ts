import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./client";
import { getOverview, getRun, listRuns, saveSettings, startDryRun } from "./endpoints";
import type { Settings } from "./types";

/** Answer every request with `body` (JSON unless it is text) and record the requests. */
function answer(status: number, body: unknown) {
  const text = typeof body === "string" ? body : JSON.stringify(body);
  const type = typeof body === "string" ? "text/html" : "application/json";
  const fetch = vi.fn<(request: Request) => Promise<Response>>(() =>
    Promise.resolve(new Response(text, { status, headers: { "Content-Type": type } })),
  );
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

/** Return the last request sent. */
function sent(fetch: ReturnType<typeof answer>): Request {
  const request = fetch.mock.calls.at(-1)?.[0];
  if (request === undefined) {
    throw new Error("No request was sent");
  }
  return request;
}

/** Return the ApiError a call fails with. */
async function failure(promise: Promise<unknown>): Promise<ApiError> {
  const error: unknown = await promise.then(
    () => undefined,
    (reason: unknown) => reason,
  );
  expect(error).toBeInstanceOf(ApiError);
  return error as ApiError;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("endpoints", () => {
  it("read the overview from the page's own origin", async () => {
    const overview = { version: "0.6.0", running: null, last_run: null, setup: null };
    const fetch = answer(200, overview);

    await expect(getOverview()).resolves.toEqual(overview);
    expect(sent(fetch).method).toBe("GET");
    expect(sent(fetch).url).toBe(`${window.location.origin}/api/status`);
  });

  it("send the History filters as query values", async () => {
    const fetch = answer(200, []);

    await listRuns({ month: "2026-10", trigger: "scheduled" });

    const url = new URL(sent(fetch).url);
    expect(url.pathname).toBe("/api/runs");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      month: "2026-10",
      trigger: "scheduled",
    });
  });

  it("put the run id in the path", async () => {
    const fetch = answer(200, { id: 7 });

    await getRun(7);

    expect(new URL(sent(fetch).url).pathname).toBe("/api/runs/7");
  });

  it("save the settings as a JSON body", async () => {
    const settings = { slots: ["18:00 - 19:00"], court: "S10" } as Settings;
    const fetch = answer(200, settings);

    await expect(saveSettings(settings)).resolves.toEqual(settings);
    const request = sent(fetch);
    expect(request.method).toBe("PUT");
    expect(request.headers.get("Content-Type")).toBe("application/json");
    expect(await request.json()).toEqual(settings);
  });

  it("start a dry run with a POST answered 202", async () => {
    const started = { pid: 4242, started_at: "2026-10-14T13:30:00" };
    const fetch = answer(202, started);

    await expect(startDryRun()).resolves.toEqual(started);
    expect(sent(fetch).method).toBe("POST");
  });
});

describe("errors", () => {
  it("carry the backend's Problem", async () => {
    answer(409, { error: "lock_held", detail: "Another run is in progress: scheduled" });

    const error = await failure(startDryRun());

    expect(error.status).toBe(409);
    expect(error.code).toBe("lock_held");
    expect(error.message).toBe("Another run is in progress: scheduled");
    expect(error.problems).toEqual([]);
  });

  it("keep each invalid value of a 422", async () => {
    answer(422, {
      error: "invalid_settings",
      detail: "a; b",
      problems: ["slots: duplicate 18:00 - 19:00", "wake_at: must be before start_at"],
    });

    const error = await failure(saveSettings({} as Settings));

    expect(error.code).toBe("invalid_settings");
    expect(error.problems).toEqual([
      "slots: duplicate 18:00 - 19:00",
      "wake_at: must be before start_at",
    ]);
  });

  it("read as unreachable when no backend answers", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("fetch failed"))),
    );

    const error = await failure(getOverview());

    expect(error.status).toBe(0);
    expect(error.code).toBe("unreachable");
  });

  it("read as unreachable when the dev proxy answers 5xx without a Problem", async () => {
    answer(502, "<html>Bad gateway</html>");

    expect((await failure(getOverview())).code).toBe("unreachable");
  });

  it("read as http for another answer without a Problem", async () => {
    answer(404, "<html>Not found</html>");

    const error = await failure(getOverview());

    expect(error.status).toBe(404);
    expect(error.code).toBe("http");
  });
});
