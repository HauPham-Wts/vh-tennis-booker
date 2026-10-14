import { useTranslation } from "react-i18next";
import { LANGUAGES } from "../i18n";
import styles from "./LanguageSwitch.module.css";

/** Switch the UI between Vietnamese and English; the language in use is pressed. */
export function LanguageSwitch() {
  const { t, i18n } = useTranslation();
  return (
    <div role="group" aria-label={t("language.label")} className={styles.group}>
      {LANGUAGES.map((language) => (
        <button
          key={language}
          type="button"
          className={styles.button}
          aria-pressed={i18n.resolvedLanguage === language}
          onClick={() => void i18n.changeLanguage(language)}
        >
          {language.toUpperCase()}
          {/* The name in its own language, so screen readers say "VI Tiếng Việt". */}
          <span className="visually-hidden" lang={language}>
            {" "}
            {t(`language.names.${language}`)}
          </span>
        </button>
      ))}
    </div>
  );
}
