import { describe, expect, it } from "vitest";
import {
  COURTS,
  courtChoices,
  findCourt,
  firstCourt,
  SLOTS,
  slotChoices,
  SPORTS,
  toggleSlot,
} from "./booking";

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

  it("adds no third slot", () => {
    const chosen = ["18:00 - 19:00", "19:00 - 20:00"];

    expect(toggleSlot(chosen, "07:00 - 08:00")).toEqual(chosen);
    expect(toggleSlot([...chosen, "20:00 - 21:00"], "07:00 - 08:00")).toHaveLength(3);
  });
});

const TENNIS = ["S6 - Sân tennis", "S8 - Sân tennis", "S9 - Sân tennis", "S10 - Sân tennis"];

describe("courtChoices", () => {
  it("offers the courts of the sport", () => {
    expect(courtChoices("tennis", "S6 - Sân tennis")).toEqual(TENNIS);
    expect(courtChoices("pickleball", "S9 - Sân Pickleball")).toEqual(["S9 - Sân Pickleball"]);
  });

  it("keeps a court set by hand as the last choice", () => {
    expect(courtChoices("tennis", "S1 - Sân tennis")).toEqual([...TENNIS, "S1 - Sân tennis"]);
  });

  it("offers only the court set by hand for a sport it does not know", () => {
    expect(courtChoices("golf", "S1 - Sân golf")).toEqual(["S1 - Sân golf"]);
  });
});

describe("the sports", () => {
  it("each have a court to start from, named once", () => {
    const names = SPORTS.flatMap((sport) => COURTS[sport].map((court) => court.name));
    expect(new Set(names).size).toBe(names.length);
    expect(SPORTS.map(firstCourt).every((court) => court !== "")).toBe(true);
  });

  it("tell their courts apart by label", () => {
    for (const sport of SPORTS) {
      const labels = COURTS[sport].map((court) => court.label);
      expect(new Set(labels).size, sport).toBe(labels.length);
    }
  });
});

describe("findCourt", () => {
  it("finds the sport and label of a court on a list", () => {
    expect(findCourt("S8 - Sân Cầu lông")).toEqual({ sport: "badminton", label: "S8" });
    expect(findCourt("S10 - Sân tập bóng rổ 01")).toEqual({
      sport: "basketball",
      label: "S10 · tập 01",
    });
  });

  it("finds no court on no list", () => {
    expect(findCourt("S1 - Sân tennis")).toBeUndefined();
  });
});
