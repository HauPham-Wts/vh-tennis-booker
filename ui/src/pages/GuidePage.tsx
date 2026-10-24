import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { ButtonLink } from "../components/ButtonLink";
import { Card } from "../components/Card";
import { PageHeader } from "../components/PageHeader";
import { paths } from "../paths";
import styles from "./GuidePage.module.css";

/** The four steps of a first setup, each a link to the screen where it is done. */
const STEPS = [
  {
    name: "device",
    to: paths.deviceSetup,
    screen: "nav.settings",
    part: "pages.deviceSetup.title",
  },
  {
    name: "booking",
    to: paths.overview,
    screen: "nav.overview",
    part: "pages.ticket.title",
  },
  {
    name: "dryRun",
    to: paths.overview,
    screen: "nav.overview",
    part: "pages.ticket.dryRun.button",
  },
  {
    name: "schedule",
    to: paths.overview,
    screen: "nav.overview",
    part: "pages.ticket.auto",
  },
] as const;

const SCREENS = ["overview", "settings"] as const;

const TROUBLES = ["notRunning", "slotFull", "quota", "loggedOut", "setup"] as const;

/**
 * Explain each screen and what to do when something fails. The page is static: it sends
 * no request.
 */
export function GuidePage() {
  const { t } = useTranslation();

  function where(screen: string, part: string): string {
    return t("pages.guide.where", { screen, part });
  }

  // The labels the texts quote come from the screens' own messages, so they always match.
  const labels = {
    history: t("pages.history.title"),
    withDry: t("pages.history.withDry"),
    technical: t("pages.history.technical"),
    ticket: t("pages.ticket.title"),
    daily: t("pages.ticket.auto"),
    device: t("pages.deviceSetup.title"),
    todo: t("pages.deviceSetup.state.todo"),
    check: t("pages.deviceSetup.manual.check"),
    auto: t("pages.deviceSetup.auto.run"),
    slotFull: t("reasons.slotFull"),
    loggedOut: t("reasons.loggedOut"),
    slotsPlace: where(t("nav.overview"), t("pages.ticket.title")),
    dryRunPlace: where(t("nav.overview"), t("pages.ticket.dryRun.button")),
  };

  return (
    <>
      <PageHeader title={t("pages.guide.title")} lead={t("pages.guide.lead")}>
        <ButtonLink to={paths.welcome}>{t("pages.guide.welcome")}</ButtonLink>
      </PageHeader>

      <section aria-labelledby="guide-start" className={styles.section}>
        <h2 id="guide-start" className={styles.title}>
          {t("pages.guide.start.title")}
        </h2>
        <ol className={styles.steps}>
          {STEPS.map((step, index) => (
            <li key={step.name}>
              <Link to={step.to} className={styles.step}>
                <span aria-hidden="true" className={styles.number}>
                  {index + 1}
                </span>
                <span className={styles.stepName}>{t(`pages.guide.start.${step.name}`)}</span>
                <span className={styles.where}>{where(t(step.screen), t(step.part))}</span>
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <Card as="section" aria-labelledby="guide-screens" className={styles.section}>
        <h2 id="guide-screens" className={styles.title}>
          {t("pages.guide.screens.title")}
        </h2>
        <dl className={styles.screens}>
          {SCREENS.map((name) => (
            <div key={name}>
              <dt>{t(`nav.${name}`)}</dt>
              <dd>{t(`pages.guide.screens.${name}`, labels)}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <section aria-labelledby="guide-trouble" className={styles.section}>
        <h2 id="guide-trouble" className={styles.title}>
          {t("pages.guide.trouble.title")}
        </h2>
        <div className={styles.troubles}>
          {TROUBLES.map((name) => (
            <details key={name} className={styles.trouble}>
              <summary>{t(`pages.guide.trouble.${name}.question`, labels)}</summary>
              <p>{t(`pages.guide.trouble.${name}.answer`, labels)}</p>
            </details>
          ))}
        </div>
      </section>
    </>
  );
}
