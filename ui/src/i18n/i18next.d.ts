import "i18next";
import type vi from "./locales/vi.json";

// Keys are checked against the Vietnamese file, so a mistyped key is a type error.
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "translation";
    resources: { translation: typeof vi };
  }
}
