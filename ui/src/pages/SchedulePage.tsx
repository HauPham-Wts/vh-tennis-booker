import { useTranslation } from "react-i18next";
import { PageTitle } from "../components/PageTitle";

/** Run a dry run and switch the daily booking on or off. */
export function SchedulePage() {
  const { t } = useTranslation();
  const title = t("pages.schedule.title");
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
    </>
  );
}
