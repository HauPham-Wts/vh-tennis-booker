import { useTranslation } from "react-i18next";
import { useOverview, useSetupChecks } from "../api/queries";
import { QueryView } from "../components/QueryView";
import styles from "./DeviceSetupPage.module.css";
import { ManualSteps } from "./setup/ManualSteps";

/**
 * Check MuMu, the app and the login, and say what is left to do. The checks ask MuMu and
 * adb, so they wait while a run holds the lock (also before the Overview has said).
 */
export function DeviceSetupPage() {
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
      <p className={styles.lead}>{t("pages.deviceSetup.lead")}</p>
      <QueryView query={overview}>
        {(data) => (
          <ManualSteps overview={data} checks={checks} running={running} onCheck={check} />
        )}
      </QueryView>
    </>
  );
}
