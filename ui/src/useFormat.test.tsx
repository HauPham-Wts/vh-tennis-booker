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
    expect(format.clock("2026-10-14T06:00:06.781")).toBe("06:00:06");
    expect(format.time("2026-10-15T06:00")).toBe("06:00");
    expect(format.seconds(7)).toBe("7,0 giây");
    expect(format.slot("18:00 - 19:00")).toBe("18:00–19:00");
    expect(format.slotStart("18:00 - 19:00")).toBe("18:00");
    expect(format.court("S6 - Sân tennis")).toBe("Tennis S6");
    expect(format.court("S10 - Sân bóng rổ nửa sân 03")).toBe("Bóng rổ S10 · nửa sân 03");
    expect(format.court("S1 - Sân tennis")).toBe("S1"); // on no list: its short name
    expect(format.courtLabel("S6 - Sân tennis")).toBe("S6");
    expect(format.courtLabel("BCX3 - Sân đa năng (Cầu lông-Pickleball)")).toBe("BCX3 · đa năng");
  });

  it("follows a switch to English", async () => {
    const { result } = renderHook(() => useFormat());

    await act(() => i18n.changeLanguage("en"));

    const format = result.current;
    expect(format.language).toBe("en");
    expect(format.day("2026-10-14")).toBe("Wed 14 Oct");
    expect(format.seconds(4.3)).toBe("4.3 s");
    // The app keeps court names in Vietnamese; the UI words their kind itself.
    expect(format.court("BE7 - Sân bóng rổ tập ném 01")).toBe("Basketball BE7 · shooting 01");
    expect(format.courtLabel("S10 - Sân bóng rổ nửa sân 03")).toBe("S10 · half court 03");
    expect(format.courtLabel("S5 - Sân bóng đá 7")).toBe("S5 · 7-a-side");
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

  it("shows what it cannot read as it is", () => {
    const { result } = renderHook(() => useFormat());

    expect(result.current.day("soon")).toBe("soon");
  });
});
