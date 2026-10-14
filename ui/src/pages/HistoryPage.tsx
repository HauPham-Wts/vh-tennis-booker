import { useTranslation } from "react-i18next";
import { PageTitle } from "../components/PageTitle";

/** List the runs with their booked slots. */
export function HistoryPage() {
  const { t } = useTranslation();
  const title = t("pages.history.title");
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
    </>
  );
}
