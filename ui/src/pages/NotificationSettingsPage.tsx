import { useTranslation } from "react-i18next";
import { errorMessage } from "../api/errors";
import {
  useSaveNotificationLanguage,
  useSaveNotifications,
  useTestNotification,
} from "../api/mutations";
import { useNotifications } from "../api/queries";
import type { NotificationSettings } from "../api/types";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { QueryView } from "../components/QueryView";
import { Switch } from "../components/Switch";
import { DEFAULT_LANGUAGE, type Language, LANGUAGES } from "../i18n";
import styles from "./NotificationSettingsPage.module.css";

/** Return the UI's language as the backend names it. */
function uiLanguage(resolved: string | undefined): Language {
  return LANGUAGES.find((language) => language === resolved) ?? DEFAULT_LANGUAGE;
}

/** The switch, saved at once, and a sample notification to see what one looks like. */
function WindowsNotification({ settings }: { settings: NotificationSettings }) {
  const { t, i18n } = useTranslation();
  const language = uiLanguage(i18n.resolvedLanguage);
  const save = useSaveNotifications();
  const saveLanguage = useSaveNotificationLanguage();
  const test = useTestNotification();
  const sending = saveLanguage.isPending || test.isPending;

  function sendTest() {
    // The sample speaks the UI's language, also when an earlier switch was not saved.
    void saveLanguage
      .mutateAsync(language)
      .catch(() => undefined)
      .finally(() => test.mutate());
  }

  return (
    <Card as="section" aria-labelledby="windows-title" className={styles.section}>
      <div className={styles.head}>
        <h2 id="windows-title" className={styles.title}>
          {t("pages.notificationSettings.windows.title")}
        </h2>
        <Switch
          label={t("pages.notificationSettings.windows.title")}
          checked={settings.enabled}
          disabled={save.isPending}
          onChange={(enabled) => save.mutate({ enabled, language })}
        />
      </div>
      <p className={styles.text}>{t("pages.notificationSettings.windows.text")}</p>
      {save.isError && <p className={styles.problem}>{errorMessage(t, save.error)}</p>}
      <div className={styles.test}>
        <Button onClick={sendTest} disabled={sending}>
          {t(
            sending
              ? "pages.notificationSettings.test.sending"
              : "pages.notificationSettings.test.send",
          )}
        </Button>
        <p aria-live="polite" className={test.isError ? styles.problem : styles.note}>
          {test.isSuccess && t("pages.notificationSettings.test.sent")}
          {test.isError && errorMessage(t, test.error)}
        </p>
      </div>
    </Card>
  );
}

/** Switch the Windows notification after every run on or off, and try it. */
export function NotificationSettingsPage() {
  const { t } = useTranslation();
  const notifications = useNotifications();
  return (
    <>
      <p className={styles.lead}>{t("pages.notificationSettings.lead")}</p>
      <QueryView query={notifications}>
        {(settings) => <WindowsNotification settings={settings} />}
      </QueryView>
    </>
  );
}
