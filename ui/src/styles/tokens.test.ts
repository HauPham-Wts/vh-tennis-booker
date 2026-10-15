import { describe, expect, it } from "vitest";
import tokensCss from "./tokens.css?raw";

// WCAG 2.2 AA: 4.5:1 for text (1.4.3), 3:1 for focus rings and state markers (1.4.11).
const TEXT_MINIMUM = 4.5;
const NON_TEXT_MINIMUM = 3;

/** Text color on background color, as token names without `--color-`. */
const TEXT_PAIRS: [string, string][] = [
  ["ink", "ground"],
  ["ink", "paper"],
  ["ink", "field"],
  ["ink", "highlight"],
  ["muted", "ground"],
  ["muted", "paper"],
  ["stamp", "ground"],
  ["stamp", "paper"],
  ["stamp-strong", "ground"],
  ["stamp-strong", "paper"],
  ["failed", "ground"],
  ["failed", "paper"],
  ["on-ink", "ink"],
  ["on-ink-muted", "ink"],
  ["code", "ink"],
];

/** Focus ring and step markers on the surfaces they sit on. */
const NON_TEXT_PAIRS: [string, string][] = [
  ["stamp", "ground"],
  ["stamp", "paper"],
  ["faint", "paper"],
];

/** Read every `--color-<name>: #rrggbb` declared in the tokens. */
function readColors(css: string): Map<string, string> {
  const colors = new Map<string, string>();
  for (const [, name = "", hex = ""] of css.matchAll(/--color-([a-z-]+):\s*(#[0-9a-f]{6})\b/gi)) {
    colors.set(name, hex);
  }
  return colors;
}

/** Return the WCAG relative luminance of a `#rrggbb` color. */
function luminance(hex: string): number {
  const [r = 0, g = 0, b = 0] = [1, 3, 5].map((start) => {
    const channel = parseInt(hex.slice(start, start + 2), 16) / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Return the WCAG contrast ratio of two colors, from 1 to 21. */
function contrast(first: string, second: string): number {
  const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return ((lighter ?? 0) + 0.05) / ((darker ?? 0) + 0.05);
}

const colors = readColors(tokensCss);

/** Return the hex value of a color token, failing the test when it is missing. */
function color(name: string): string {
  const hex = colors.get(name);
  if (hex === undefined) {
    throw new Error(`tokens.css has no --color-${name}`);
  }
  return hex;
}

describe("contrast", () => {
  it("measures black on white as 21:1 and a color on itself as 1:1", () => {
    expect(contrast("#000000", "#ffffff")).toBeCloseTo(21, 5);
    expect(contrast("#2b48a6", "#2b48a6")).toBeCloseTo(1, 5);
  });
});

describe("design tokens", () => {
  it.each(TEXT_PAIRS)("keeps %s text readable on %s", (text, background) => {
    expect(contrast(color(text), color(background))).toBeGreaterThanOrEqual(TEXT_MINIMUM);
  });

  it.each(NON_TEXT_PAIRS)("keeps %s marks visible on %s", (mark, background) => {
    expect(contrast(color(mark), color(background))).toBeGreaterThanOrEqual(NON_TEXT_MINIMUM);
  });
});
