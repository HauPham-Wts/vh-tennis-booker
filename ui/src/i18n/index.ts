import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import vi from "./locales/vi.json";

/** The UI languages; Vietnamese comes first and is the default. */
export const LANGUAGES = ["vi", "en"] as const;
export type Language = (typeof LANGUAGES)[number];
export const DEFAULT_LANGUAGE: Language = "vi";

/** Where the chosen language is kept on this machine (the app's WebView storage). */
export const STORAGE_KEY = "court-booker.language";

export const resources = {
  vi: { translation: vi },
  en: { translation: en },
} as const;

function isLanguage(value: unknown): value is Language {
  return LANGUAGES.some((language) => language === value);
}

/** Return the language chosen earlier, or the default when none is stored or readable. */
export function readStoredLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return isLanguage(stored) ? stored : DEFAULT_LANGUAGE;
  } catch {
    // Storage can be blocked; the app then opens in the default language.
    return DEFAULT_LANGUAGE;
  }
}

// Registered before init, so the first language also sets the page's lang and is stored.
i18n.on("languageChanged", (language) => {
  document.documentElement.lang = language;
  try {
    localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Without storage the choice lasts until the window closes.
  }
});

void i18n.use(initReactI18next).init({
  resources,
  lng: readStoredLanguage(),
  fallbackLng: DEFAULT_LANGUAGE,
  // React escapes text itself.
  interpolation: { escapeValue: false },
});

export default i18n;
