import { describe, expect, it } from "vitest";
import i18n from "../i18n";
import { ApiError } from "./client";
import { ERROR_CODES, errorCode, errorMessage } from "./errors";

const vietnamese = i18n.getFixedT("vi");
const english = i18n.getFixedT("en");

/** An ApiError with `code`, as the client builds it from a Problem. */
function apiError(code: string): ApiError {
  return new ApiError(409, { error: code, detail: "English detail for the log" });
}

describe("errorMessage", () => {
  it("translates a backend code into the current language", () => {
    expect(errorMessage(vietnamese, apiError("lock_held"))).toBe(
      "Đang có một lần chạy khác. Hãy chờ nó xong rồi thử lại.",
    );
    expect(errorMessage(english, apiError("lock_held"))).toBe(
      "Another run is in progress. Try again when it has finished.",
    );
  });

  it("reads an unknown code as a general error", () => {
    expect(errorCode(apiError("something_new"))).toBe("engine");
    expect(errorMessage(english, apiError("something_new"))).toBe("Court Booker hit an error.");
  });

  it("reads an error that is not from the API as a general error", () => {
    expect(errorCode(new TypeError("x is undefined"))).toBe("engine");
  });

  it.each(ERROR_CODES)("has a message for %s in both languages", (code) => {
    for (const t of [vietnamese, english]) {
      const message = errorMessage(t, apiError(code));
      expect(message).not.toBe(`errors.${code}`);
      expect(message.length).toBeGreaterThan(0);
    }
  });
});
