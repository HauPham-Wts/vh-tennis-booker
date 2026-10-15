import { afterEach, describe, expect, it, vi } from "vitest";
import i18n, { readStoredLanguage, STORAGE_KEY } from ".";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("readStoredLanguage", () => {
  it("opens in Vietnamese when nothing is stored", () => {
    expect(readStoredLanguage()).toBe("vi");
  });

  it("opens in the language chosen earlier", () => {
    localStorage.setItem(STORAGE_KEY, "en");

    expect(readStoredLanguage()).toBe("en");
  });

  it("ignores a stored value that is not a UI language", () => {
    localStorage.setItem(STORAGE_KEY, "fr");

    expect(readStoredLanguage()).toBe("vi");
  });

  it("opens in Vietnamese when the storage cannot be read", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("Storage is blocked");
    });

    expect(readStoredLanguage()).toBe("vi");
  });
});

describe("changing the language", () => {
  it("still switches when the storage cannot be written", async () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("Storage is blocked");
    });

    await i18n.changeLanguage("en");

    expect(i18n.resolvedLanguage).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });
});
