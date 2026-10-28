import { useTranslation } from "react-i18next";
import { errorMessage } from "../../api/errors";
import { useSaveNotifications } from "../../api/mutations";
import { useNotifications } from "../../api/queries";
import { Switch } from "../../components/Switch";
import { DEFAULT_LANGUAGE, LANGUAGES } from "../../i18n";
import styles from "./BookingTicket.module.css";

/**
 * The Windows notification after every run, as a switch on the ticket beside the daily one,
 * saved at once. It shows once the setting is read; a failed save says why below it.
 */
export function NotifySwitch() {
  const { t, i18n } = useTranslation();
  const notifications = useNotifications();
  const save = useSaveNotifications();
  // The notification speaks the UI's language; the switch saves it along.
  const language = LANGUAGES.find((known) => known === i18n.resolvedLanguage) ?? DEFAULT_LANGUAGE;
  if (notifications.data === undefined) {
    return null;
  }
  const label = t("pages.ticket.notify");
  return (
    <>
      <div className={styles.auto} title={t("pages.ticket.notifyHint")}>
        <span aria-hidden="true">{label}</span>
        <Switch
          label={label}
          checked={notifications.data.enabled}
          disabled={save.isPending}
          onChange={(enabled) => save.mutate({ enabled, language })}
          onText={t("pages.ticket.on")}
          offText={t("pages.ticket.off")}
        />
      </div>
      {save.isError && <p className={styles.problem}>{errorMessage(t, save.error)}</p>}
    </>
  );
}
