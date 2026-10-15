import { paths } from "../../paths";

/** The welcome steps in order; the address holds the number (`/welcome?step=2`). */
export const STEPS = ["intro", "device", "booking", "schedule"] as const;

/** Read the step from the address: 1 to 4, else the first. */
export function stepNumber(value: string | null): number {
  const step = Number(value);
  return Number.isInteger(step) && step >= 1 && step <= STEPS.length ? step : 1;
}

/** The address of a step. */
export function stepPath(step: number) {
  return { pathname: paths.welcome, search: `?step=${step}` };
}
