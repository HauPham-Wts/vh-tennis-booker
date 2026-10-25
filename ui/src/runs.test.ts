import { describe, expect, it } from "vitest";
import i18n from "./i18n";
import { runMark, runOrigin, runStamp } from "./runs";

const vi_ = i18n.getFixedT("vi");
const en = i18n.getFixedT("en");

const run = (fields: Partial<Parameters<typeof runStamp>[1]>) => ({
  dry_run: false,
  status: "ok",
  booked: 2,
  total: 2,
  ...fields,
});

describe("runStamp", () => {
  it.each([
    [run({}), "ĐÃ ĐẶT 2/2", "booked"],
    [run({ status: "partial", booked: 1 }), "ĐẶT ĐƯỢC 1/2", "failed"],
    [run({ status: "failed", booked: 0 }), "KHÔNG ĐƯỢC 0/2", "failed"],
    [run({ status: "failed", booked: 0, total: 0 }), "KHÔNG ĐẶT ĐƯỢC", "failed"],
    [run({ dry_run: true }), "CHẠY THỬ ĐẠT", "muted"],
    [run({ dry_run: true, status: "partial", booked: 1 }), "CHẠY THỬ ĐẠT 1/2", "failed"],
    [run({ dry_run: true, status: "failed", booked: 0, total: 0 }), "CHẠY THỬ LỖI", "failed"],
    [run({ status: "interrupted", booked: 1 }), "ĐÃ DỪNG", "failed"],
    [run({ status: "running", booked: 0, total: 0 }), "ĐANG CHẠY", "booked"],
  ])("stamps %j as %j", (counts, text, tone) => {
    expect(runStamp(vi_, counts)).toEqual({ text, tone });
  });

  it("stamps in English", () => {
    expect(runStamp(en, run({})).text).toBe("BOOKED 2/2");
    expect(runStamp(en, run({ status: "failed", booked: 0 })).text).toBe("NOT BOOKED 0/2");
    expect(runStamp(en, run({ dry_run: true, booked: 0 })).text).toBe("DRY RUN FAILED");
  });
});

describe("runMark", () => {
  it.each([
    [run({}), "2/2", "booked"],
    [run({ status: "partial", booked: 1 }), "1/2", "failed"],
    [run({ status: "failed", booked: 0 }), "0/2", "failed"],
    [run({ status: "failed", booked: 0, total: 0 }), "✕", "failed"],
    [run({ dry_run: true }), "THỬ", "muted"],
    [run({ dry_run: true, status: "partial", booked: 1 }), "THỬ 1/2", "failed"],
    [run({ dry_run: true, status: "failed", booked: 0, total: 0 }), "THỬ ✕", "failed"],
    [run({ status: "interrupted", booked: 1 }), "DỪNG", "failed"],
    [run({ status: "running", booked: 0, total: 0 }), "ĐANG CHẠY", "booked"],
  ])("marks %j as %j", (counts, text, tone) => {
    expect(runMark(vi_, counts)).toEqual({ text, tone });
  });

  it("marks a dry run in English", () => {
    expect(runMark(en, run({ dry_run: true })).text).toBe("DRY");
  });
});

describe("runOrigin", () => {
  it("says how a run started, and an unknown value", () => {
    expect(runOrigin(vi_, "scheduled")).toBe("theo hẹn giờ");
    expect(runOrigin(vi_, "manual")).toBe("chạy tay");
    expect(runOrigin(en, "dry_run")).toBe("dry run");
    expect(runOrigin(vi_, "cron")).toBe("không rõ");
  });
});
