import { act, renderHook } from "@testing-library/react";
import { useTranslation } from "react-i18next";
import { describe, expect, it } from "vitest";
import i18n from "./i18n";
import { failureReason } from "./reasons";
import { useFormat } from "./useFormat";

async function reasonOf(reason: string | null, language: "vi" | "en" = "vi") {
  await act(() => i18n.changeLanguage(language));
  const { result } = renderHook(() => ({ t: useTranslation().t, f: useFormat() }));
  return failureReason(result.current.t, result.current.f, reason);
}

describe("failureReason", () => {
  // The reasons as the engine writes them (flow.py, runner.py, cli.py), seen in real runs.
  it.each([
    ["Slot 18:00 - 19:00 is fully booked", "Hết chỗ"],
    ["Court S6 - Sân tennis is fully booked", "Sân S6 đã kín"],
    [
      "The app refused the booking: Căn hộ đã hết hạn mức đăng ký tiện ích cho phép.",
      "App từ chối: Căn hộ đã hết hạn mức đăng ký tiện ích cho phép.",
    ],
    [
      "2026-10-17 18:00 - 19:00 not open after 3 attempt(s): Date 2026-10-17 is not bookable",
      "Ngày chưa mở đặt",
    ],
    ["Tapped 'Tiếp tục' but the next screen did not appear", "App không chuyển màn hình"],
    ["Another run is in progress: dry_run run (pid 17156) since 11:12:48", "Đang có lần chạy khác"],
    ["AdbShellError(AdbTimeout('adb read timeout'))", "Có lỗi, xem nhật ký"],
    [null, "Có lỗi, xem nhật ký"],
  ])("words %j as %j", async (reason, words) => {
    expect(await reasonOf(reason)).toBe(words);
  });

  it("words the reasons in English", async () => {
    expect(await reasonOf("Slot 18:00 - 19:00 is fully booked", "en")).toBe("Fully booked");
    expect(await reasonOf("Court S6 - Sân tennis is fully booked", "en")).toBe(
      "Court S6 fully booked",
    );
  });
});
