import { describe, expect, it } from "vitest";
import {
  formatClock,
  formatDateTime,
  formatDay,
  formatDecimal,
  formatShortDate,
  formatTime,
  monthParts,
  parseLocal,
} from "./format";

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

describe("dates", () => {
  it.each([
    ["2026-10-14", "vi", "Thứ Tư 14/10"],
    ["2026-10-14", "en", "Wed 14 Oct"],
    ["2026-10-18", "vi", "Chủ Nhật 18/10"],
    ["2026-10-18", "en", "Sun 18 Oct"],
    ["2026-11-02", "vi", "Thứ Hai 02/11"],
    ["2026-11-02", "en", "Mon 2 Nov"],
    ["2026-12-31T23:59:59", "vi", "Thứ Năm 31/12"],
    ["2027-01-01T00:00:00", "en", "Fri 1 Jan"],
  ] as const)("formatDay(%j, %s) is %j", (text, language, expected) => {
    expect(formatDay(text, language)).toBe(expected);
  });

  it.each([
    ["2026-10-09", "vi", "09/10"],
    ["2026-10-09", "en", "9 Oct"],
    ["2026-10-16T06:00:07.177", "vi", "16/10"],
  ] as const)("formatShortDate(%j, %s) is %j", (text, language, expected) => {
    expect(formatShortDate(text, language)).toBe(expected);
  });

  it.each([
    ["2026-10-12T06:00:11.056", "vi", "12/10 06:00"],
    ["2026-10-12T19:43:00", "en", "12 Oct 19:43"],
  ] as const)("formatDateTime(%j, %s) is %j", (text, language, expected) => {
    expect(formatDateTime(text, language)).toBe(expected);
  });

  it("shows a text it cannot read as it is", () => {
    expect(formatDay("soon", "vi")).toBe("soon");
    expect(formatShortDate("", "en")).toBe("");
    expect(formatDateTime("2026-02-30T06:00", "vi")).toBe("2026-02-30T06:00");
  });
});

describe("times", () => {
  it("writes 24-hour times with leading zeros", () => {
    expect(formatClock("2026-10-14T06:00:06.781")).toBe("06:00:06");
    expect(formatClock("2026-10-14T19:05")).toBe("19:05:00");
    expect(formatTime("2026-10-15T06:00")).toBe("06:00");
    expect(formatTime("2026-10-14T21:30:59")).toBe("21:30");
  });

  it("gives the first moment of a date alone", () => {
    expect(formatClock("2026-10-16")).toBe("00:00:00");
  });

  it("shows a text it cannot read as it is", () => {
    expect(formatClock("06:00")).toBe("06:00");
    expect(formatTime("later")).toBe("later");
  });
});

describe("numbers", () => {
  it.each([
    [7, "vi", "7,0"],
    [7, "en", "7.0"],
    [22.44, "vi", "22,4"],
    [4.25, "en", "4.3"],
    [0, "vi", "0,0"],
  ] as const)("formatDecimal(%j, %s) is %j", (value, language, expected) => {
    expect(formatDecimal(value, language)).toBe(expected);
  });
});

describe("monthParts", () => {
  it("names the month in each language", () => {
    expect(monthParts("2026-10", "vi")).toEqual({ month: 10, year: 2026, name: "Tháng 10" });
    expect(monthParts("2026-10", "en")).toEqual({ month: 10, year: 2026, name: "October" });
  });

  it.each(["2026-13", "2026-00", "2026-1", "10/2026", ""])("gives null for %j", (text) => {
    expect(monthParts(text, "en")).toBeNull();
  });
});
