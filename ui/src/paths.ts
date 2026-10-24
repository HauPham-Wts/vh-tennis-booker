/** The address of every screen; paths stay English in both languages. */
export const paths = {
  overview: "/",
} as const;

/**
 * The addresses of the screens the home screen replaced. They lead to it, keeping the
 * query: a `?run=` of the old History opens that run in the panel.
 */
export const OLD_PATHS = [
  "/schedule",
  "/history/*",
  "/activity",
  "/settings/*",
  "/guide",
  "/welcome",
] as const;
