import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { manualDone, setManualDone, STORAGE_KEY, useManualSteps } from "./manualSteps";

afterEach(() => {
  vi.restoreAllMocks();
  vi.resetModules();
});

describe("manual steps", () => {
  it("start unticked", () => {
    expect(manualDone()).toEqual({ mumu: false, app: false, login: false });
  });

  it("keep a tick in the browser's storage", () => {
    setManualDone("app", true);

    expect(manualDone()).toEqual({ mumu: false, app: true, login: false });
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "")).toEqual({
      mumu: false,
      app: true,
      login: false,
    });
  });

  it("read anything else stored as unticked", () => {
    localStorage.setItem(STORAGE_KEY, "not json");
    expect(manualDone()).toEqual({ mumu: false, app: false, login: false });

    localStorage.setItem(STORAGE_KEY, JSON.stringify({ mumu: "yes", login: true }));
    expect(manualDone()).toEqual({ mumu: false, app: false, login: true });
  });

  it("keep the app and the login for each machine, MuMu for all", () => {
    setManualDone("mumu", true);
    setManualDone("app", true, "1");

    expect(manualDone()).toEqual({ mumu: true, app: false, login: false });
    expect(manualDone("1")).toEqual({ mumu: true, app: true, login: false });
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "") as { machines: unknown };
    expect(stored.machines).toEqual({
      "1": { mumu: true, app: true, login: false },
    });
  });

  it("tell the screens that show them", () => {
    const { result } = renderHook(() => useManualSteps());

    act(() => setManualDone("mumu", true));

    expect(result.current.mumu).toBe(true);
  });

  it("stay in memory when storage fails", async () => {
    // A fresh module, so the failure does not reach the other tests.
    const fresh = await import("./manualSteps");
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });

    fresh.setManualDone("login", true);

    expect(fresh.manualDone()).toEqual({ mumu: false, app: false, login: true });
  });

  it("stay in memory when storage cannot be read", async () => {
    const fresh = await import("./manualSteps");
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });

    expect(fresh.manualDone()).toEqual({ mumu: false, app: false, login: false });
    fresh.setManualDone("mumu", true);
    expect(fresh.manualDone().mumu).toBe(true);
  });
});
