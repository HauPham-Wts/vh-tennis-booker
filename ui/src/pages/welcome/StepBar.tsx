import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import styles from "./StepBar.module.css";
import { STEPS, stepPath } from "./steps";

/**
 * The four welcome steps as a bar of links, the current one in ink. Any step can be opened:
 * none has to be finished first.
 */
export function StepBar({ current }: { current: number }) {
  const { t } = useTranslation();
  const currentLink = useRef<HTMLAnchorElement>(null);
  const shown = useRef(current);

  // "Tiếp" sits at the bottom of a step: moving focus to the new step in the bar brings the
  // top of the page back into view and tells screen readers which step this is.
  useEffect(() => {
    if (shown.current !== current) {
      shown.current = current;
      currentLink.current?.focus();
    }
  }, [current]);

  return (
    <nav aria-label={t("pages.welcome.steps")}>
      <ol className={styles.steps}>
        {STEPS.map((name, index) => {
          const step = index + 1;
          const here = step === current;
          return (
            <li key={name}>
              <Link
                ref={here ? currentLink : undefined}
                to={stepPath(step)}
                aria-current={here ? "step" : undefined}
                className={styles.step}
              >
                {t("pages.welcome.step", {
                  number: step,
                  name: t(`pages.welcome.names.${name}`),
                })}
              </Link>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
