import { describe, expect, it } from "vitest";
import { COURTS, courtChoices, SLOTS, slotChoices, toggleSlot } from "./booking";

describe("slotChoices", () => {
  it("splits the app's 13 slots into morning and afternoon", () => {
    const { morning, afternoon } = slotChoices([]);

    expect(morning).toEqual(SLOTS.slice(0, 6));
    expect(afternoon).toEqual(SLOTS.slice(6));
    expect(morning.length + afternoon.length).toBe(13);
  });

  it("keeps a slot set by hand, in time order, once", () => {
    const { morning, afternoon } = slotChoices(["12:00 - 13:00", "15:00 - 16:00"]);

    expect(morning).toEqual(SLOTS.slice(0, 6));
    expect(afternoon.slice(0, 2)).toEqual(["12:00 - 13:00", "14:00 - 15:00"]);
    expect(afternoon).toHaveLength(8);
  });
});

describe("toggleSlot", () => {
  it("adds a slot after the ones chosen, so it is booked last", () => {
    expect(toggleSlot(["18:00 - 19:00"], "07:00 - 08:00")).toEqual([
      "18:00 - 19:00",
      "07:00 - 08:00",
    ]);
  });

  it("removes a chosen slot and keeps the order of the rest", () => {
    const chosen = ["18:00 - 19:00", "07:00 - 08:00", "19:00 - 20:00"];

    expect(toggleSlot(chosen, "07:00 - 08:00")).toEqual(["18:00 - 19:00", "19:00 - 20:00"]);
  });
});

describe("courtChoices", () => {
  it("offers the venue's courts", () => {
    expect(courtChoices("S6 - Sân tennis")).toEqual([...COURTS]);
  });

  it("keeps a court set by hand as the last choice", () => {
    expect(courtChoices("S1 - Sân tennis")).toEqual([...COURTS, "S1 - Sân tennis"]);
  });
});
