import { describe, expect, it } from "vitest";
import { newestDays, playDay, runDay } from "./days";

describe("runDay and playDay", () => {
  it("read the day a run started, and its day of play when it has one", () => {
    const run = { started_at: "2026-10-15T05:50:02.120", play_date: "2026-10-17" };

    expect(runDay(run)).toBe("2026-10-15");
    expect(playDay(run)).toBe("2026-10-17");
    expect(playDay({ ...run, play_date: null })).toBe("2026-10-15");
  });
});

describe("newestDays", () => {
  const items = ["10-18 a", "10-18 b", "10-17 a", "10-18 c", "10-12 a", "10-16 a"];
  const day = (item: string) => item.slice(0, 5);

  it("keeps every item of the newest days, in their order", () => {
    expect(newestDays(items, day, 2)).toEqual({
      shown: ["10-18 a", "10-18 b", "10-17 a", "10-18 c"],
      more: true,
    });
  });

  it("counts only the days that have items", () => {
    expect(newestDays(items, day, 3).shown).toEqual([
      "10-18 a",
      "10-18 b",
      "10-17 a",
      "10-18 c",
      "10-16 a",
    ]);
  });

  it("says nothing is left out once every day is shown", () => {
    expect(newestDays(items, day, 4)).toEqual({ shown: items, more: false });
    expect(newestDays([], day, 10)).toEqual({ shown: [], more: false });
  });
});
