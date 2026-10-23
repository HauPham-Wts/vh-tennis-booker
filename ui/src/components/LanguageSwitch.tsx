import { useTranslation } from "react-i18next";
import { useSaveNotificationLanguage } from "../api/mutations";
import { type Language, LANGUAGES } from "../i18n";
import styles from "./LanguageSwitch.module.css";

/**
 * Switch the UI between Vietnamese and English; the language in use is pressed. A switch
 * the user makes also gives the Windows notification that language.
 */
export function LanguageSwitch() {
  const { t, i18n } = useTranslation();
  const saveLanguage = useSaveNotificationLanguage();

  function choose(language: Language) {
    void i18n.changeLanguage(language);
    saveLanguage.mutate(language);
  }

  return (
    <div role="group" aria-label={t("language.label")} className={styles.group}>
      {LANGUAGES.map((language) => {
        const code = language.toUpperCase();
        return (
          <button
            key={language}
            type="button"
            className={styles.button}
            // The visible code, then the language named in itself: "VI Tiếng Việt".
            aria-label={`${code} ${t(`language.names.${language}`)}`}
            aria-pressed={i18n.resolvedLanguage === language}
            onClick={() => choose(language)}
          >
            {code}
          </button>
        );
      })}
    </div>
  );
}
