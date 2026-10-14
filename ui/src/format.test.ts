import { describe, expect, it } from "vitest";
import { parseLocal } from "./format";

describe("parseLocal", () => {
  it("reads a date-time with milliseconds as written", () => {
    expect(parseLocal("2026-10-14T06:00:06.123")).toEqual({
      year: 2026,
      month: 10,
      day: 14,
      hour: 6,
      minute: 0,
      second: 6,
    });
  });

  it("reads a date-time to the minute", () => {
    expect(parseLocal("2026-10-15T06:00")).toMatchObject({ hour: 6, minute: 0, second: 0 });
  });

  it("reads a date alone as its first moment, without shifting the day", () => {
    expect(parseLocal("2026-10-16")).toEqual({
      year: 2026,
      month: 10,
      day: 16,
      hour: 0,
      minute: 0,
      second: 0,
    });
  });

  it.each([
    "",
    "16/10/2026",
    "2026-10-16Z",
    "2026-10-16T06:00:00+07:00",
    "2026-02-30",
    "2026-13-01",
    "2026-10-16T24:00",
    "2026-10-16T06:60",
  ])("gives null for %j", (text) => {
    expect(parseLocal(text)).toBeNull();
  });
});
