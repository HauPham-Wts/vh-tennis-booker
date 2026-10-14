import { describe, expect, it } from "vitest";
import i18n from "./i18n";
import { runResult, runStamp, triggerName } from "./runs";

const vi_ = i18n.getFixedT("vi");
const en = i18n.getFixedT("en");

const run = (fields: Partial<Parameters<typeof runResult>[0]>) => ({
  dry_run: false,
  status: "ok",
  booked: 2,
  total: 2,
  ...fields,
});

describe("runStamp", () => {
  it.each([
    [run({}), "ĐẶT ĐƯỢC 2/2", "booked"],
    [run({ status: "partial", booked: 1 }), "ĐẶT ĐƯỢC 1/2", "failed"],
    [run({ status: "failed", booked: 0 }), "KHÔNG ĐẶT ĐƯỢC", "failed"],
    [run({ dry_run: true }), "CHẠY THỬ ĐẠT 2/2", "booked"],
    [run({ dry_run: true, status: "partial", booked: 1 }), "CHẠY THỬ ĐẠT 1/2", "failed"],
    [run({ dry_run: true, status: "failed", booked: 0, total: 0 }), "CHẠY THỬ LỖI", "failed"],
    [run({ status: "interrupted", booked: 1 }), "ĐÃ DỪNG", "failed"],
    [run({ status: "running", booked: 0, total: 0 }), "ĐANG CHẠY", "booked"],
  ])("stamps %j as %j", (counts, text, tone) => {
    expect(runStamp(vi_, counts)).toEqual({ text, tone });
  });

  it("stamps in English", () => {
    expect(runStamp(en, run({})).text).toBe("BOOKED 2/2");
    expect(runStamp(en, run({ dry_run: true, booked: 0 })).text).toBe("DRY RUN FAILED");
  });
});

describe("runResult", () => {
  it.each([
    [run({}), "✓ 2/2", "booked"],
    [run({ status: "partial", booked: 1 }), "✕ 1/2", "failed"],
    [run({ status: "failed", booked: 0, total: 1 }), "✕ 0/1", "failed"],
    [run({ status: "failed", booked: 0, total: 0 }), "✕", "failed"],
    [run({ status: "interrupted", booked: 2 }), "✕ 2/2", "failed"],
    [run({ status: "running", booked: 0, total: 0 }), "…", "plain"],
  ])("marks %j as %j", (counts, text, tone) => {
    expect(runResult(counts)).toEqual({ text, tone });
  });
});

describe("triggerName", () => {
  it("names what started a run, and an unknown value", () => {
    expect(triggerName(vi_, "scheduled")).toBe("hẹn giờ");
    expect(triggerName(en, "dry_run")).toBe("dry run");
    expect(triggerName(vi_, "cron")).toBe("không rõ");
    expect(triggerName(vi_, undefined)).toBe("không rõ");
  });
});
