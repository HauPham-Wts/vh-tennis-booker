import { useTranslation } from "react-i18next";
import { PageTitle } from "../components/PageTitle";

/** Check MuMu, the app and the wake timers, and fix what can be fixed. */
export function DeviceSetupPage() {
  const { t } = useTranslation();
  const title = t("pages.deviceSetup.title");
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <h2>{title}</h2>
    </>
  );
}
