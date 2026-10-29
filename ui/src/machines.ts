/**
 * The machines the home screen shows, one at a time: the top of the settings first, then
 * their `[[instances]]` in order, each a MuMu instance with its own account. There are
 * always two at least: without an instance, the second is MuMu instance 1, switched off
 * (it books only once switched on, which adds its instance).
 */
import { useMemo } from "react";
import { useSettings } from "./api/queries";
import type { Settings } from "./api/types";

export interface Machine {
  /** 0 for the top of the settings, then each instance in order. */
  place: number;
  /** Its MuMu instance, `null` until the settings have loaded. */
  mumuIndex: number | null;
  /** Where its ticks are kept: "" for the first, else its MuMu index. */
  key: string;
  /** Whether the runs book with it; the first always does. */
  enabled: boolean;
}

/** The one machine known before the settings load. */
const FIRST: Machine = { place: 0, mumuIndex: null, key: "", enabled: true };

/** The MuMu instance a second machine switched off would use: the first one free. */
function spareIndex(settings: Settings): number {
  return settings.mumu_index === 1 ? 0 : 1;
}

/** Return the machines of `settings`, the first alone until they have loaded. */
export function machinesOf(settings: Settings | undefined): Machine[] {
  if (settings === undefined) {
    return [FIRST];
  }
  const machines = [settings, ...settings.instances].map((item, place) => ({
    place,
    mumuIndex: item.mumu_index,
    key: place === 0 ? "" : String(item.mumu_index),
    enabled: true,
  }));
  if (machines.length === 1) {
    const index = spareIndex(settings);
    machines.push({ place: 1, mumuIndex: index, key: String(index), enabled: false });
  }
  return machines;
}

/** Return machine `place`, the last if it is gone. */
export function machineAt(machines: readonly Machine[], place: number): Machine {
  return machines[Math.min(place, machines.length - 1)] ?? FIRST;
}

/** Return the machines the runs book with. */
export function enabledMachines(machines: readonly Machine[]): Machine[] {
  return machines.filter((machine) => machine.enabled);
}

/** Read the machines from the settings. */
export function useMachines(): Machine[] {
  const settings = useSettings();
  return useMemo(() => machinesOf(settings.data), [settings.data]);
}
