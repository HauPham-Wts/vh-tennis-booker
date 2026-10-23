import type { TFunction } from "i18next";
import { ApiError } from "./client";

/**
 * The codes an ApiError carries: the backend's Problem codes (court_booker.api.errors) and
 * the client's own `unreachable` and `http`. Each has a message in the language files.
 */
export const ERROR_CODES = [
  "not_found",
  "lock_held",
  "dry_run_required",
  "bad_request",
  "device",
  "app_not_ready",
  "schedule",
  "notification",
  "engine",
  "invalid_settings",
  "invalid_request",
  "unreachable",
  "http",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];

/** Return the code of any error; one the UI does not know reads as a general `engine` error. */
export function errorCode(error: unknown): ErrorCode {
  if (error instanceof ApiError) {
    const known = ERROR_CODES.find((code) => code === error.code);
    if (known !== undefined) {
      return known;
    }
  }
  return "engine";
}

/** Return the message for an error in the current language, never a raw code. */
export function errorMessage(t: TFunction, error: unknown): string {
  return t(`errors.${errorCode(error)}`);
}
