import { useMutation, useQueryClient } from "@tanstack/react-query";
import { runAutoSetup, saveSettings, startDryRun, switchSchedule } from "./endpoints";
import { queryKeys } from "./queries";

/** Save the booking settings; the overview and the schedule show the new times. */
export function useSaveSettings() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: saveSettings,
    onSuccess: async (settings) => {
      cache.setQueryData(queryKeys.settings, settings);
      await Promise.all([
        cache.invalidateQueries({ queryKey: queryKeys.overview }),
        cache.invalidateQueries({ queryKey: queryKeys.schedule }),
        cache.invalidateQueries({ queryKey: ["events"] }),
      ]);
    },
  });
}

/** Run auto setup; its checks replace the cached ones and the overview shows what is left. */
export function useAutoSetup() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: runAutoSetup,
    onSuccess: async (items) => {
      cache.setQueryData(queryKeys.setup, items);
      await Promise.all([
        cache.invalidateQueries({ queryKey: queryKeys.overview }),
        cache.invalidateQueries({ queryKey: ["events"] }),
      ]);
    },
  });
}

/** Switch the daily schedule on or off. */
export function useSwitchSchedule() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: switchSchedule,
    onSuccess: async (schedule) => {
      cache.setQueryData(queryKeys.schedule, schedule);
      await Promise.all([
        cache.invalidateQueries({ queryKey: queryKeys.overview }),
        cache.invalidateQueries({ queryKey: ["events"] }),
      ]);
    },
  });
}

/** Start a dry run; the overview shows it running, the live feed brings its steps. */
export function useStartDryRun() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: startDryRun,
    onSuccess: () => cache.invalidateQueries({ queryKey: queryKeys.overview }),
  });
}
