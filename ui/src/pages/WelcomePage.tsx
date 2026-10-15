import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { useOverview } from "../api/queries";
import { ButtonLink } from "../components/ButtonLink";
import { PageTitle } from "../components/PageTitle";
import { QueryView } from "../components/QueryView";
import { paths } from "../paths";
import { markWelcomeShown } from "../welcome";
import { Intro } from "./welcome/Intro";
import { StepBar } from "./welcome/StepBar";
import { STEPS, stepNumber, stepPath } from "./welcome/steps";
import styles from "./WelcomePage.module.css";

/**
 * The way on from a step: "Để sau" back to the Overview, and back and on between the steps.
 * Step 1 goes on from its own "Bắt đầu thiết lập"; the last step ends on the Overview.
 */
function Moves({ step }: { step: number }) {
  const { t } = useTranslation();
  const last = step === STEPS.length;
  return (
    <div className={styles.moves}>
      <Link to={paths.overview} className={styles.later}>
        {t("pages.welcome.later")}
      </Link>
      {step > 1 && (
        <div className={styles.buttons}>
          <ButtonLink to={stepPath(step - 1)}>{t("pages.welcome.back")}</ButtonLink>
          <ButtonLink variant="primary" to={last ? paths.overview : stepPath(step + 1)}>
            {t(last ? "pages.welcome.done" : "pages.welcome.next")}
          </ButtonLink>
        </div>
      )}
    </div>
  );
}

/**
 * Walk a first-time user through four steps: what Court Booker does, the device setup, the
 * slots and the schedule. Steps 2 to 4 are the screens the app already has. No step has to
 * be finished to go on.
 */
export function WelcomePage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const step = stepNumber(params.get("step"));
  const overview = useOverview();
  // Once seen, the Overview stops sending the user here until the app opens again.
  useEffect(markWelcomeShown, []);
  return (
    <>
      <PageTitle>{t("pages.welcome.title")}</PageTitle>
      <StepBar current={step} />
      {step === 1 && (
        <QueryView query={overview}>{({ schedule }) => <Intro schedule={schedule} />}</QueryView>
      )}
      {step === 2 && <h1 className={styles.title}>{t("pages.deviceSetup.title")}</h1>}
      {step === 3 && <h1 className={styles.title}>{t("pages.guide.start.booking")}</h1>}
      {step === 4 && <h1 className={styles.title}>{t("pages.schedule.title")}</h1>}
      <Moves step={step} />
    </>
  );
}
