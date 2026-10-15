import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useOverview, useSetupChecks } from "../api/queries";
import { QueryView } from "../components/QueryView";
import styles from "./DeviceSetupPage.module.css";
import { AutoSetup } from "./setup/AutoSetup";
import { ManualSteps } from "./setup/ManualSteps";

/**
 * Check MuMu, the app and the login, say what is left for the user, and let auto setup do
 * the rest. The checks ask MuMu and adb, so they wait while a run holds the lock (also
 * before the Overview has said).
 */
export function DeviceSetupPage({ title }: { title?: ReactNode }) {
  const { t } = useTranslation();
  const overview = useOverview();
  const running = overview.data?.running !== null;
  const checks = useSetupChecks(!running);

  function check() {
    void checks.refetch();
    void overview.refetch();
  }

  return (
    <>
      {/* A title of the screen's own (the Welcome step) stays as close as a page header's. */}
      <div className={styles.heading}>
        {title}
        <p className={styles.lead}>{t("pages.deviceSetup.lead")}</p>
      </div>
      <QueryView query={overview}>
        {(data) => (
          <>
            <ManualSteps overview={data} checks={checks} running={running} onCheck={check} />
            <AutoSetup overview={data} checks={checks} running={running} />
          </>
        )}
      </QueryView>
    </>
  );
}
