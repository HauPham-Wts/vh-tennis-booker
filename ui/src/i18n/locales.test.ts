import { describe, expect, it } from "vitest";
import { LANGUAGES, resources } from ".";

type Messages = { readonly [key: string]: string | Messages };

/** Flatten nested messages into "a.b.c" keys and their texts. */
function flatten(messages: Messages, prefix = ""): Map<string, string> {
  const entries = new Map<string, string>();
  for (const [key, value] of Object.entries(messages)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") {
      entries.set(path, value);
    } else {
      for (const [inner, text] of flatten(value, path)) {
        entries.set(inner, text);
      }
    }
  }
  return entries;
}

/** Return the {{placeholders}} of a message, sorted. */
function placeholders(text: string): string[] {
  return [...text.matchAll(/\{\{\s*(\w+)\s*\}\}/g)].map(([, name = ""]) => name).sort();
}

const flat = Object.fromEntries(
  LANGUAGES.map((language) => [language, flatten(resources[language].translation)]),
) as Record<(typeof LANGUAGES)[number], Map<string, string>>;

describe("language files", () => {
  it("hold the same keys in Vietnamese and English", () => {
    expect([...flat.en.keys()].sort()).toEqual([...flat.vi.keys()].sort());
  });

  it.each(LANGUAGES)("leave no %s message empty", (language) => {
    const empty = [...flat[language]].filter(([, text]) => text.trim() === "").map(([key]) => key);
    expect(empty).toEqual([]);
  });

  it("use the same placeholders in both languages", () => {
    for (const [key, text] of flat.vi) {
      expect(placeholders(flat.en.get(key) ?? ""), key).toEqual(placeholders(text));
    }
  });
});
