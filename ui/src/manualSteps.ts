/**
 * The setup steps only the user can do (install MuMu, install the Vinhomes app, log in),
 * ticked by the user. The app does not check them: the ticks live in this browser's storage
 * and never reach the backend. Storage that fails keeps them until the window closes; lost
 * ticks are ticked again.
 */
import { useSyncExternalStore } from "react";

/** Where the ticks are kept in `localStorage`. */
export const STORAGE_KEY = "court-booker.setup";

/** The steps, in the order the user does them. */
export const MANUAL_STEPS = ["mumu", "app", "login"] as const;

export type ManualStep = (typeof MANUAL_STEPS)[number];
export type ManualDone = Readonly<Record<ManualStep, boolean>>;

const NONE: ManualDone = { mumu: false, app: false, login: false };

const listeners = new Set<() => void>();
/** The ticks as storage would hold them, read instead once storage has failed. */
let memory: string | null = null;
let storageFailed = false;
let lastText: string | null | undefined;
let lastDone: ManualDone = NONE;

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

function parse(text: string | null): ManualDone {
  try {
    const value: unknown = JSON.parse(text ?? "{}");
    if (typeof value !== "object" || value === null) {
      return NONE;
    }
    const stored = value as Partial<Record<string, unknown>>;
    return {
      mumu: stored["mumu"] === true,
      app: stored["app"] === true,
      login: stored["login"] === true,
    };
  } catch {
    return NONE;
  }
}

/** Return which steps are ticked; the same object while nothing changed. */
export function manualDone(): ManualDone {
  const text = storedText();
  if (text !== lastText) {
    lastText = text;
    lastDone = parse(text);
  }
  return lastDone;
}

/** Tick a step or take its tick off, and tell every screen that shows the ticks. */
export function setManualDone(step: ManualStep, done: boolean): void {
  const text = JSON.stringify({ ...manualDone(), [step]: done });
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

/** Read the ticks and follow their changes. */
export function useManualSteps(): ManualDone {
  return useSyncExternalStore(subscribe, manualDone);
}
