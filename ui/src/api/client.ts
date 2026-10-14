import createClient from "openapi-fetch";
import type { Problem, paths } from "./types";

/**
 * A failed request: the backend's Problem, or `unreachable` when no backend answered and
 * `http` for an answer that is not a Problem. `code` is what the UI translates.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly problems: readonly string[];

  constructor(status: number, problem: Problem) {
    super(problem.detail);
    this.name = "ApiError";
    this.status = status;
    this.code = problem.error;
    this.problems = problem.problems ?? [];
  }
}

function isProblem(body: unknown): body is Problem {
  if (typeof body !== "object" || body === null) {
    return false;
  }
  const { error, detail } = body as Record<string, unknown>;
  return typeof error === "string" && typeof detail === "string";
}

/** Turn a failed response into an ApiError. */
function toApiError(status: number, body: unknown): ApiError {
  if (isProblem(body)) {
    return new ApiError(status, body);
  }
  // Vite's proxy answers 5xx without a Problem when the backend is not running.
  const code = status >= 500 ? "unreachable" : "http";
  return new ApiError(status, { error: code, detail: `HTTP ${status} without a Problem body` });
}

/** The backend, typed by the generated paths; requests go to the page's own origin. */
export const client = createClient<paths>({
  baseUrl: window.location.origin,
  // Look fetch up on every call, so tests can stand in for the network.
  fetch: (request) => globalThis.fetch(request),
});

interface Result<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/** Wait for a request of `client` and return its body, or throw an ApiError. */
export async function call<T>(request: Promise<Result<T>>): Promise<T> {
  let result: Result<T>;
  try {
    result = await request;
  } catch (cause) {
    const detail = cause instanceof Error ? cause.message : String(cause);
    throw new ApiError(0, { error: "unreachable", detail });
  }
  if (!result.response.ok || result.error !== undefined) {
    throw toApiError(result.response.status, result.error);
  }
  return result.data as T;
}
