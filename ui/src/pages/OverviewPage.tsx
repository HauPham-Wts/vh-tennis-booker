import { useTranslation } from "react-i18next";
import { PageTitle } from "../components/PageTitle";

/** Show the next booking, the last run and recent history. */
export function OverviewPage() {
  const { t } = useTranslation();
  const title = t("pages.overview.title");
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
    </>
  );
}
