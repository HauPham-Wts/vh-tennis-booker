/**
 * The setup steps only the user can do (install MuMu, install the Vinhomes app, log in),
 * ticked by the user. The app does not check them: the ticks live in this browser's storage
 * and never reach the backend. Storage that fails keeps them until the window closes; lost
 * ticks are ticked again.
 *
 * MuMu is installed once; the app and the login are ticked for each machine (each MuMu
 * instance has its own account). The first machine's ticks sit at the top of what is stored,
 * as before there could be more; another's under `machines`, by its MuMu index.
 */
import { useSyncExternalStore } from "react";

/** Where the ticks are kept in `localStorage`. */
export const STORAGE_KEY = "court-booker.setup";

/** The steps, in the order the user does them. */
export const MANUAL_STEPS = ["mumu", "app", "login"] as const;

/** The steps done once for every machine. */
export const SHARED_STEPS: readonly ManualStep[] = ["mumu"];

export type ManualStep = (typeof MANUAL_STEPS)[number];
export type ManualDone = Readonly<Record<ManualStep, boolean>>;

/** Every tick: the first machine's (and the shared ones), and each other machine's. */
export interface ManualTicks {
  readonly first: ManualDone;
  readonly machines: Readonly<Record<string, ManualDone>>;
}

const NONE: ManualDone = { mumu: false, app: false, login: false };
const NO_TICKS: ManualTicks = { first: NONE, machines: {} };

const listeners = new Set<() => void>();
/** The ticks as storage would hold them, read instead once storage has failed. */
let memory: string | null = null;
let storageFailed = false;
let lastText: string | null | undefined;
let lastTicks: ManualTicks = NO_TICKS;

function storedText(): string | null {
  if (storageFailed) {
    return memory;
  }
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    storageFailed = true;
    return memory;
  }
}

function isRecord(value: unknown): value is Partial<Record<string, unknown>> {
  return typeof value === "object" && value !== null;
}

function doneIn(stored: Partial<Record<string, unknown>>): ManualDone {
  return {
    mumu: stored["mumu"] === true,
    app: stored["app"] === true,
    login: stored["login"] === true,
  };
}

function parse(text: string | null): ManualTicks {
  try {
    const value: unknown = JSON.parse(text ?? "{}");
    if (!isRecord(value)) {
      return NO_TICKS;
    }
    const stored = value["machines"];
    const machines: Record<string, ManualDone> = {};
    if (isRecord(stored)) {
      for (const [key, done] of Object.entries(stored)) {
        if (isRecord(done)) {
          machines[key] = doneIn(done);
        }
      }
    }
    return { first: doneIn(value), machines };
  } catch {
    return NO_TICKS;
  }
}

/** Return every tick; the same object while nothing changed. */
export function manualTicks(): ManualTicks {
  const text = storedText();
  if (text !== lastText) {
    lastText = text;
    lastTicks = parse(text);
  }
  return lastTicks;
}

/** Return which steps are ticked for machine `key` ("" the first), the shared ones included. */
export function doneOf(ticks: ManualTicks, key = ""): ManualDone {
  if (key === "") {
    return ticks.first;
  }
  const own = ticks.machines[key] ?? NONE;
  return { ...own, mumu: ticks.first.mumu };
}

/** Return which steps are ticked for machine `key` ("" the first). */
export function manualDone(key = ""): ManualDone {
  return doneOf(manualTicks(), key);
}

/** Tick a step of machine `key` or take its tick off, and tell every screen that shows it. */
export function setManualDone(step: ManualStep, done: boolean, key = ""): void {
  const ticks = manualTicks();
  const next =
    key === "" || SHARED_STEPS.includes(step)
      ? { ...ticks.first, [step]: done, machines: ticks.machines }
      : {
          ...ticks.first,
          machines: { ...ticks.machines, [key]: { ...doneOf(ticks, key), [step]: done } },
        };
  // One machine stores as before there could be more.
  const text = JSON.stringify(
    Object.keys(next.machines).length === 0 ? { ...next, machines: undefined } : next,
  );
  memory = text;
  try {
    localStorage.setItem(STORAGE_KEY, text);
  } catch {
    // Blocked or full storage: the ticks stay in memory until the window closes.
    storageFailed = true;
  }
  for (const listener of listeners) {
    listener();
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Read every tick and follow their changes. */
export function useManualTicks(): ManualTicks {
  return useSyncExternalStore(subscribe, manualTicks);
}

/** Read the ticks of machine `key` ("" the first) and follow their changes. */
export function useManualSteps(key = ""): ManualDone {
  return doneOf(useManualTicks(), key);
}
