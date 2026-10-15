import { useTranslation } from "react-i18next";
import type { ScheduleState } from "../../api/types";
import { ButtonLink } from "../../components/ButtonLink";
import { Overline } from "../../components/Overline";
import { Ticket } from "../../components/Ticket";
import styles from "./Intro.module.css";
import { stepPath } from "./steps";

/** What the user prepares before the setup. */
const NEEDS = ["mumu", "app", "account"] as const;

/**
 * Step 1: what Court Booker does every morning, with the times of this PC's schedule, and
 * what the user needs before setting it up.
 */
export function Intro({ schedule }: { schedule: ScheduleState }) {
  const { t } = useTranslation();
  const { wake_at: wake, start_at: start } = schedule;
  return (
    <>
      <div className={styles.hero}>
        <h1 className={styles.title}>{t("pages.welcome.intro.title", { start })}</h1>
        <p className={styles.lead}>{t("pages.welcome.intro.lead", { start })}</p>
      </div>

      <section aria-labelledby="morning-title" className={styles.morning}>
        <Overline as="h2" id="morning-title">
          {t("pages.welcome.intro.morning")}
        </Overline>
        <ol className={styles.moments}>
          <li className={styles.moment}>
            <span className={styles.when}>{wake}</span>
            <span className={styles.what}>{t("pages.welcome.intro.wake.title")}</span>
            <span className={styles.text}>{t("pages.welcome.intro.wake.text")}</span>
          </li>
          <li className={styles.moment}>
            <span className={styles.when}>{t("pages.welcome.intro.open.when")}</span>
            <span className={styles.what}>{t("pages.welcome.intro.open.title")}</span>
            <span className={styles.text}>{t("pages.welcome.intro.open.text")}</span>
          </li>
          <li className={`${styles.moment} ${styles.start}`}>
            <span className={styles.when}>
              <mark>{start}</mark>
            </span>
            <span className={styles.what}>{t("pages.welcome.intro.book.title")}</span>
            <span className={styles.text}>{t("pages.welcome.intro.book.text")}</span>
          </li>
        </ol>
      </section>

      <Ticket
        as="section"
        aria-labelledby="need-title"
        stub={
          <>
            <p className={styles.privacy}>{t("pages.welcome.intro.need.privacy")}</p>
            <ButtonLink variant="primary" size="large" to={stepPath(2)}>
              {t("pages.welcome.intro.need.start")}
            </ButtonLink>
          </>
        }
      >
        <h2 id="need-title" className={styles.needTitle}>
          {t("pages.welcome.intro.need.title")}
        </h2>
        <ul className={styles.needs}>
          {NEEDS.map((need) => (
            <li key={need}>
              <strong>{t(`pages.welcome.intro.need.${need}.name`)}</strong>{" "}
              {t(`pages.welcome.intro.need.${need}.text`)}
            </li>
          ))}
        </ul>
        <p className={styles.note}>{t("pages.welcome.intro.need.note")}</p>
      </Ticket>
    </>
  );
}
