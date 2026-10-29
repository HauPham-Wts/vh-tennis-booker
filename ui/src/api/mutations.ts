import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Language } from "../i18n";
import {
  getNotifications,
  saveNotifications,
  saveSettings,
  startDryRun,
  switchSchedule,
} from "./endpoints";
import { queryKeys } from "./queries";

/** Save the booking settings; the overview shows the next booking with them. */
export function useSaveSettings() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: saveSettings,
    onSuccess: async (settings) => {
      cache.setQueryData(queryKeys.settings, settings);
      await Promise.all([
        cache.invalidateQueries({ queryKey: queryKeys.overview }),
        cache.invalidateQueries({ queryKey: ["events"] }),
      ]);
    },
  });
}

/** Save the notification settings; the activity log shows the save. */
export function useSaveNotifications() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: saveNotifications,
    onSuccess: async (settings) => {
      cache.setQueryData(queryKeys.notifications, settings);
      await cache.invalidateQueries({ queryKey: ["events"] });
    },
  });
}

/**
 * Give the notification the language the user just chose for the UI, saving only when it
 * differs. A failure leaves the UI in its new language and the notification in the old.
 */
export function useSaveNotificationLanguage() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: async (language: Language) => {
      const saved = await cache.fetchQuery({
        queryKey: queryKeys.notifications,
        queryFn: getNotifications,
      });
      return saved.language === language ? saved : saveNotifications({ ...saved, language });
    },
    onSuccess: async (settings) => {
      cache.setQueryData(queryKeys.notifications, settings);
      await cache.invalidateQueries({ queryKey: ["events"] });
    },
  });
}

/** Switch the daily schedule on or off; the overview shows its new state. */
export function useSwitchSchedule() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: switchSchedule,
    onSuccess: async () => {
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
