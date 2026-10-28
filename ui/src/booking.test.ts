import { describe, expect, it } from "vitest";
import {
  courtChoices,
  findCourt,
  firstCourt,
  inSubdivision,
  isCourtKind,
  isSport,
  SLOTS,
  type Subdivision,
  SUBDIVISIONS,
  shownSubdivision,
  slotChoices,
  sportChoices,
  subdivisionOf,
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
const ORIGAMI = subdivisionOf("origami") as Subdivision;
const BS = subdivisionOf("bs") as Subdivision;

describe("shownSubdivision", () => {
  it("shows the subdivision the settings name first", () => {
    expect(shownSubdivision("bs", "origami").id).toBe("bs");
  });

  it("follows the account while the settings name none", () => {
    expect(shownSubdivision("", "bs").id).toBe("bs");
  });

  it("falls back to Origami", () => {
    expect(shownSubdivision("", undefined).id).toBe("origami");
    expect(shownSubdivision("khu-b", "khu-c").id).toBe("origami");
  });
});

describe("sportChoices", () => {
  it("offers the sports of the subdivision in the app's order", () => {
    expect(sportChoices(BS, "tennis")).toEqual([
      "volleyball",
      "tennis",
      "basketball",
      "football",
      "pickleball",
      "badminton",
    ]);
  });

  it("keeps a sport the subdivision lacks as the last choice", () => {
    expect(sportChoices(BS, "multi").at(-1)).toBe("multi");
  });
});

describe("courtChoices", () => {
  it("offers the courts of the sport in the subdivision", () => {
    expect(courtChoices(ORIGAMI, "tennis", "S6 - Sân tennis")).toEqual(TENNIS);
    expect(courtChoices(BS, "tennis", "BE7 - Sân tennis")).toEqual([
      "BE7 - Sân tennis",
      "BCX3 - Sân tennis 01",
      "BCX3 - Sân tennis 02",
      "CX2 - Sân tennis 01",
      "CX2 - Sân tennis 02",
    ]);
  });

  it("keeps a court set by hand as the last choice", () => {
    expect(courtChoices(ORIGAMI, "tennis", "S1 - Sân tennis")).toEqual([
      ...TENNIS,
      "S1 - Sân tennis",
    ]);
  });

  it("offers only the court set by hand for a sport it does not know", () => {
    expect(courtChoices(ORIGAMI, "golf", "S1 - Sân golf")).toEqual(["S1 - Sân golf"]);
  });
});

describe("inSubdivision", () => {
  it("keeps the sport the new subdivision has, with its first court", () => {
    expect(inSubdivision(BS, "tennis")).toEqual({
      subdivision: "bs",
      sport: "tennis",
      court: "BE7 - Sân tennis",
    });
  });

  it("takes the first sport of the new subdivision otherwise", () => {
    expect(inSubdivision(BS, "table-tennis")).toEqual({
      subdivision: "bs",
      sport: "volleyball",
      court: "BCX3 - Sân bóng chuyền hơi 01",
    });
  });
});

describe("the catalog", () => {
  it("names each sport in the language files, with a court to start from", () => {
    for (const subdivision of SUBDIVISIONS) {
      for (const sport of subdivision.sports) {
        expect(isSport(sport.id), sport.id).toBe(true);
        expect(firstCourt(subdivision, sport.id), sport.id).not.toBe("");
      }
    }
  });

  it("words every kind of court in the language files", () => {
    for (const subdivision of SUBDIVISIONS) {
      for (const sport of subdivision.sports) {
        for (const court of sport.courts) {
          expect(court.kind === "" || isCourtKind(court.kind), court.name).toBe(true);
        }
      }
    }
  });

  it("tells the courts of a sport apart by label", () => {
    for (const subdivision of SUBDIVISIONS) {
      for (const sport of subdivision.sports) {
        const labels = sport.courts.map((court) => `${court.code} ${court.kind} ${court.number}`);
        expect(new Set(labels).size, `${subdivision.id} ${sport.id}`).toBe(labels.length);
      }
    }
  });
});

describe("findCourt", () => {
  it("finds the subdivision, sport and court of a name in the catalog", () => {
    const badminton = findCourt("S8 - Sân Cầu lông");
    expect([badminton?.subdivision.id, badminton?.sport, badminton?.court.code]).toEqual([
      "origami",
      "badminton",
      "S8",
    ]);
    const basketball = findCourt("BE7 - Sân bóng rổ tập ném 01");
    expect(basketball?.subdivision.id).toBe("bs");
    expect(basketball?.court).toEqual({
      name: "BE7 - Sân bóng rổ tập ném 01",
      code: "BE7",
      kind: "shooting",
      number: "01",
    });
  });

  it("finds no court the catalog lacks", () => {
    expect(findCourt("S1 - Sân tennis")).toBeUndefined();
  });
});
