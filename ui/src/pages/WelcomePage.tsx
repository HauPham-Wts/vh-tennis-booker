import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { useOverview } from "../api/queries";
import { Button } from "../components/Button";
import { ButtonLink } from "../components/ButtonLink";
import { PageTitle } from "../components/PageTitle";
import { QueryView } from "../components/QueryView";
import { paths } from "../paths";
import { markWelcomeShown } from "../welcome";
import { BookingSettingsPage } from "./BookingSettingsPage";
import { DeviceSetupPage } from "./DeviceSetupPage";
import { ScheduleSteps } from "./schedule/ScheduleSteps";
import { Intro } from "./welcome/Intro";
import { StepBar } from "./welcome/StepBar";
import { STEPS, stepNumber, stepPath } from "./welcome/steps";
import styles from "./WelcomePage.module.css";

interface MovesProps {
  step: number;
  /** The step holds changes not saved yet: going on would lose them. */
  unsaved: boolean;
}

/**
 * The way on from a step: "Để sau" back to the Overview, and back and on between the steps.
 * Step 1 goes on from its own "Bắt đầu thiết lập"; the last step ends on the Overview.
 */
function Moves({ step, unsaved }: MovesProps) {
  const { t } = useTranslation();
  const last = step === STEPS.length;
  return (
    <div className={styles.moves}>
      <Link to={paths.overview} className={styles.later}>
        {t("pages.welcome.later")}
      </Link>
      {step > 1 && (
        <div className={styles.buttons}>
          {unsaved && (
            <p id="unsaved-note" className={styles.unsaved}>
              {t("pages.welcome.unsaved", {
                save: t("pages.bookingSettings.save"),
                cancel: t("pages.bookingSettings.cancel"),
              })}
            </p>
          )}
          <ButtonLink to={stepPath(step - 1)}>{t("pages.welcome.back")}</ButtonLink>
          {unsaved ? (
            <Button variant="primary" disabled aria-describedby="unsaved-note">
              {t("pages.welcome.next")}
            </Button>
          ) : (
            <ButtonLink variant="primary" to={last ? paths.overview : stepPath(step + 1)}>
              {t(last ? "pages.welcome.done" : "pages.welcome.next")}
            </ButtonLink>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Walk a first-time user through four steps: what Court Booker does, the device setup, the
 * slots and the schedule. Steps 2 to 4 are the screens the app already has. No step has to
 * be finished to go on, but slots chosen and not saved hold "Tiếp" back.
 */
export function WelcomePage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const step = stepNumber(params.get("step"));
  const overview = useOverview();
  const [unsaved, setUnsaved] = useState(false);
  const start = overview.data?.schedule.start_at;
  // Once seen, the Overview stops sending the user here until the app opens again.
  useEffect(markWelcomeShown, []);
  return (
    <>
      <PageTitle>{t("pages.welcome.title")}</PageTitle>
      <StepBar current={step} />
      {step === 1 && (
        <QueryView query={overview}>{({ schedule }) => <Intro schedule={schedule} />}</QueryView>
      )}
      {step === 2 && (
        <>
          <h1 className={styles.title}>{t("pages.deviceSetup.title")}</h1>
          <DeviceSetupPage />
        </>
      )}
      {step === 3 && (
        <>
          <h1 className={styles.title}>{t("pages.guide.start.booking")}</h1>
          <BookingSettingsPage onUnsavedChange={setUnsaved} />
        </>
      )}
      {step === 4 && (
        <>
          <div className={styles.heading}>
            <h1 className={styles.title}>{t("pages.schedule.title")}</h1>
            {start !== undefined && (
              <p className={styles.lead}>{t("pages.schedule.lead", { start })}</p>
            )}
          </div>
          <ScheduleSteps />
        </>
      )}
      <Moves step={step} unsaved={step === 3 && unsaved} />
    </>
  );
}
