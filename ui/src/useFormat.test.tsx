import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import i18n from "./i18n";
import { useFormat } from "./useFormat";

describe("useFormat", () => {
  it("formats in Vietnamese by default, with the words of the language file", () => {
    const { result } = renderHook(() => useFormat());
    const format = result.current;

    expect(format.language).toBe("vi");
    expect(format.day("2026-10-14")).toBe("Thứ Tư 14/10");
    expect(format.shortDate("2026-10-09")).toBe("09/10");
    expect(format.dateTime("2026-10-12T06:00:11")).toBe("12/10 06:00");
    expect(format.clock("2026-10-14T06:00:06.781")).toBe("06:00:06");
    expect(format.time("2026-10-15T06:00")).toBe("06:00");
    expect(format.seconds(7)).toBe("7,0 giây");
    expect(format.period("2026-10-15T05:50")).toBe("sáng");
    expect(format.period("2026-10-15T14:00")).toBe("chiều");
    expect(format.period("2026-10-15T19:43")).toBe("tối");
    expect(format.slot("18:00 - 19:00")).toBe("18:00–19:00");
    expect(format.slotStart("18:00 - 19:00")).toBe("18:00");
    expect(format.court("S6 - Sân tennis")).toBe("S6");
  });

  it("follows a switch to English", async () => {
    const { result } = renderHook(() => useFormat());

    await act(() => i18n.changeLanguage("en"));

    const format = result.current;
    expect(format.language).toBe("en");
    expect(format.day("2026-10-14")).toBe("Wed 14 Oct");
    expect(format.dateTime("2026-10-12T19:43:00")).toBe("12 Oct 19:43");
    expect(format.seconds(4.3)).toBe("4.3 s");
    expect(format.period("2026-10-15T05:50")).toBe("morning");
  });

  it("says when a time falls, near today or not", async () => {
    const { result } = renderHook(() => useFormat());
    const today = "2026-10-15";

    expect(result.current.when("2026-10-15T05:50:02", today)).toBe("sáng nay");
    expect(result.current.when("2026-10-16T06:00", today)).toBe("sáng mai");
    expect(result.current.when("2026-10-14T19:43:00", today)).toBe("tối hôm qua");
    expect(result.current.when("2026-10-12T09:40:00", today)).toBe("sáng Thứ Hai 12/10");
    expect(result.current.when("soon", today)).toBe("soon");

    await act(() => i18n.changeLanguage("en"));
    expect(result.current.when("2026-10-16T06:00", today)).toBe("tomorrow morning");
    expect(result.current.when("2026-10-15T14:00", today)).toBe("this afternoon");
    expect(result.current.when("2026-10-12T09:40:00", today)).toBe("Mon 12 Oct morning");
  });

  it("shows what it cannot read as it is, or nothing for a period", () => {
    const { result } = renderHook(() => useFormat());

    expect(result.current.period("soon")).toBe("");
  });
});
