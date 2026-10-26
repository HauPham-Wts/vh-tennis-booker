import { act, renderHook } from "@testing-library/react";
import { useTranslation } from "react-i18next";
import { describe, expect, it } from "vitest";
import type { Step } from "./api/types";
import i18n from "./i18n";
import { type StepMessage, stepMessage } from "./steps";
import { step } from "./test/liveSocket";
import { useFormat } from "./useFormat";

/** Describe a step of `kind` with `data` in `language`. */
async function describeStep(
  language: "vi" | "en",
  kind: Step["kind"],
  data: Step["data"] = {},
): Promise<StepMessage> {
  await act(() => i18n.changeLanguage(language));
  const { result } = renderHook(() => ({ t: useTranslation().t, f: useFormat() }));
  return stepMessage(result.current.t, result.current.f, step(1, { kind, data }));
}

/** Every step as the engine and the app record it, with its Vietnamese words and tone. */
const CASES: [Step["kind"], Step["data"], string, StepMessage["tone"]][] = [
  ["run_started", { trigger: "scheduled" }, "Bắt đầu theo hẹn giờ", "plain"],
  ["run_started", { trigger: "dry_run" }, "Bắt đầu chạy thử", "plain"],
  ["run_started", { trigger: "manual" }, "Bắt đầu chạy thủ công", "plain"],
  ["device_ready", {}, "Đã mở MuMu", "plain"],
  ["app_ready", {}, "Đã mở app Vinhomes", "plain"],
  ["waiting", { until: "2026-10-15T05:59:00" }, "Chờ đến 05:59:00", "plain"],
  [
    "booking_started",
    { date: "2026-10-17", court: "S6 - Sân tennis", slots: [], dry_run: false },
    "Bắt đầu đặt cho Thứ Bảy 17/10 · sân Tennis S6",
    "moment",
  ],
  [
    "slot_started",
    { slot: "15:00 - 16:00", round: 1, rounds: 2 },
    "Lượt 1/2: 15:00–16:00",
    "plain",
  ],
  ["calendar_opened", { attempt: 1 }, "Đã mở lịch đặt sân", "plain"],
  ["calendar_opened", { attempt: 3 }, "Đã mở lịch đặt sân (lần 3)", "plain"],
  ["date_selected", { date: "2026-10-17" }, "Đã chọn ngày Thứ Bảy 17/10", "plain"],
  ["slot_selected", { slot: "15:00 - 16:00", swipes: 0 }, "Đã chọn khung 15:00–16:00", "plain"],
  ["court_selected", { court: "S6 - Sân tennis" }, "Đã chọn sân Tennis S6", "plain"],
  ["terms_accepted", {}, "Đã tích đồng ý điều khoản", "plain"],
  [
    "slot_booked",
    { slot: "15:00 - 16:00", seconds: 6, commands: 54, dry_run: false },
    "Đặt được 15:00–16:00",
    "booked",
  ],
  [
    "slot_booked",
    { slot: "10:00 - 11:00", seconds: 8.8, commands: 49, dry_run: true },
    "Chạy thử tới bước xác nhận: 10:00–11:00",
    "booked",
  ],
  [
    "slot_failed",
    { slot: "15:00 - 16:00", reason: "Court S6 - Sân tennis is fully booked", seconds: 7.2 },
    "Không đặt được 15:00–16:00",
    "failed",
  ],
  [
    "run_finished",
    { status: "ok", booked: 2, total: 2, error: null },
    "Xong: 2/2 khung thành công",
    "booked",
  ],
  [
    "run_finished",
    { status: "partial", booked: 1, total: 2, error: null },
    "Xong: 1/2 khung thành công",
    "failed",
  ],
  [
    "run_finished",
    { status: "failed", booked: 0, total: 2, error: null },
    "Xong: không khung nào thành công",
    "failed",
  ],
  [
    "run_finished",
    { status: "failed", booked: 0, total: 0, error: "MuMu did not start" },
    "Dừng vì lỗi",
    "failed",
  ],
  ["run_finished", { status: "interrupted", booked: 0, total: 0 }, "Đã dừng giữa chừng", "failed"],
  [
    "lock_cleared",
    { trigger: "manual", pid: 1, since: "" },
    "Đã gỡ khóa của một lần chạy đã dừng",
    "plain",
  ],
  ["lock_waiting", { trigger: "dry_run" }, "Chờ lần chạy khác xong (chạy thử)", "plain"],
  [
    "lock_taken_over",
    { trigger: "setup" },
    "Đã dừng lần chạy khác (thiết lập tự động) để kịp giờ đặt",
    "failed",
  ],
  ["setup_started", { restart_mumu: false }, "Bắt đầu thiết lập tự động", "plain"],
  [
    "setup_item",
    { item: "mumu_screen", status: "fixed", detail: "Screen set to 540x1600" },
    "Màn hình MuMu 540x1600: đã sửa",
    "booked",
  ],
  [
    "setup_item",
    { item: "app_installed", status: "user", detail: "Install the app" },
    "App Vinhomes trong MuMu: cần bạn tự làm",
    "failed",
  ],
  [
    "setup_item",
    { item: "app_installed", status: "unknown", detail: "MuMu is off" },
    "App Vinhomes trong MuMu: chưa kiểm tra được",
    "plain",
  ],
  ["setup_finished", { left: [], error: null }, "Thiết lập tự động xong", "booked"],
  [
    "setup_finished",
    { left: ["app_installed"], error: null },
    "Thiết lập xong, số mục cần bạn làm: 1",
    "failed",
  ],
  [
    "setup_finished",
    { left: [], error: "powercfg failed" },
    "Thiết lập tự động dừng vì lỗi",
    "failed",
  ],
  ["settings_saved", { changed: ["slots", "court"] }, "Đã lưu cài đặt (số mục đổi: 2)", "plain"],
  [
    "schedule_enabled",
    { wake_at: "05:50", start_at: "06:00" },
    "Đã bật hẹn giờ: đánh thức máy 05:50, đặt lúc 06:00",
    "booked",
  ],
  ["schedule_disabled", {}, "Đã tắt hẹn giờ", "plain"],
];

describe("stepMessage", () => {
  it.each(CASES)("words %s %j in Vietnamese", async (kind, data, words, tone) => {
    const message = await describeStep("vi", kind, data);

    expect(message.text).toBe(words);
    expect(message.tone).toBe(tone);
  });

  it.each(CASES)("words %s %j in English, with nothing left unfilled", async (kind, data) => {
    const message = await describeStep("en", kind, data);

    expect(message.text).not.toBe("");
    expect(message.text).not.toMatch(/\{\{|undefined|null|NaN|steps\./);
  });

  it("adds the time a slot took and keeps the engine's reason for the details", async () => {
    const failed = await describeStep("vi", "slot_failed", {
      slot: "15:00 - 16:00",
      reason: "Court S6 - Sân tennis is fully booked",
      seconds: 7.2,
    });
    expect(failed.extra).toBe("7,2 giây");
    expect(failed.detail).toBe("Court S6 - Sân tennis is fully booked");

    const booked = await describeStep("en", "slot_booked", { slot: "15:00 - 16:00", seconds: 6 });
    expect(booked.text).toBe("Booked 15:00–16:00");
    expect(booked.extra).toBe("6.0 s");
  });

  it("keeps the error of a run that stopped for the details", async () => {
    const message = await describeStep("vi", "run_finished", {
      status: "failed",
      booked: 0,
      total: 0,
      error: "MuMu did not start",
    });

    expect(message.detail).toBe("MuMu did not start");
  });

  it("writes a sentence without the value when a step lacks it", async () => {
    const cases: [Step["kind"], string][] = [
      ["run_started", "Bắt đầu"],
      ["waiting", "Chờ đến giờ đặt"],
      ["booking_started", "Bắt đầu đặt"],
      ["slot_started", "Bắt đầu một lượt"],
      ["calendar_opened", "Đã mở lịch đặt sân"],
      ["date_selected", "Đã chọn ngày"],
      ["slot_selected", "Đã chọn khung giờ"],
      ["court_selected", "Đã chọn sân"],
      ["slot_booked", "Đặt được một khung giờ"],
      ["slot_failed", "Không đặt được một khung giờ"],
      ["run_finished", "Xong"],
      ["lock_waiting", "Chờ lần chạy khác xong (không rõ)"],
      ["setup_item", "Đã kiểm tra một mục thiết lập"],
      ["setup_finished", "Thiết lập tự động xong"],
      ["settings_saved", "Đã lưu cài đặt"],
      ["schedule_enabled", "Đã bật hẹn giờ"],
    ];
    for (const [kind, words] of cases) {
      const message = await describeStep("vi", kind, {});
      expect(message.text, kind).toBe(words);
      expect(message.extra, kind).toBeUndefined();
    }
  });

  it("ignores values of the wrong type", async () => {
    const message = await describeStep("vi", "slot_started", {
      slot: 15,
      round: "1",
      rounds: null,
    });

    expect(message.text).toBe("Bắt đầu một lượt");
  });

  it("names a step kind it does not know instead of failing", async () => {
    const message = await describeStep("vi", "a_newer_step" as Step["kind"]);

    expect(message).toEqual({ text: "Bước khác (a_newer_step)", tone: "plain" });
  });
});
