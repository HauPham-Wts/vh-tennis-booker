import { useTranslation } from "react-i18next";
import { LANGUAGES } from "../i18n";
import styles from "./LanguageSwitch.module.css";

/** Switch the UI between Vietnamese and English; the language in use is pressed. */
export function LanguageSwitch() {
  const { t, i18n } = useTranslation();
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
            onClick={() => void i18n.changeLanguage(language)}
          >
            {code}
          </button>
        );
      })}
    </div>
  );
}
