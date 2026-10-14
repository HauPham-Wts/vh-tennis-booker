import { QueryClient } from "@tanstack/react-query";
import { errorCode } from "./errors";

/** How often a read is tried again while the backend is out of reach. */
export const UNREACHABLE_RETRIES = 3;

/**
 * How long a read counts as fresh. The live feed marks what each step changes as stale at
 * once, so this only keeps a return to the window from reading everything again.
 */
export const FRESH_MS = 30_000;

/**
 * Retry a read only while no backend answers (it may be starting); a Problem it sent, such
 * as `not_found` or `lock_held`, will not change by asking again.
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  return errorCode(error) === "unreachable" && failureCount < UNREACHABLE_RETRIES;
}

/** Build the cache of backend data the screens share. */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, staleTime: FRESH_MS },
      // A save or a dry run must never run twice behind the user's back.
      mutations: { retry: false },
    },
  });
}
