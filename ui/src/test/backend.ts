import { vi } from "vitest";

/** A stand-in answer of the backend. */
export interface Reply {
  status: number;
  body: unknown;
}

/** Answer with `body` as JSON and HTTP `status` (200 unless given). */
export function reply(body: unknown, status = 200): Reply {
  return { status, body };
}

/**
 * Stand in for the backend: answer each "METHOD /path" with its reply and record every
 * request. A request without a reply gets a not_found Problem that names it.
 */
export function stubBackend(replies: Record<string, Reply>) {
  const fetch = vi.fn<(request: Request) => Promise<Response>>((request) => {
    const key = `${request.method} ${new URL(request.url).pathname}`;
    const { status, body } =
      replies[key] ?? reply({ error: "not_found", detail: `No stub for ${key}` }, 404);
    const headers = { "Content-Type": "application/json" };
    return Promise.resolve(new Response(JSON.stringify(body), { status, headers }));
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

/** Count the requests a stub received for "METHOD /path". */
export function requestsTo(fetch: ReturnType<typeof stubBackend>, key: string): number {
  return fetch.mock.calls.filter(
    ([request]) => `${request.method} ${new URL(request.url).pathname}` === key,
  ).length;
}
