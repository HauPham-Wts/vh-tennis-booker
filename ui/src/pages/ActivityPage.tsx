import { useTranslation } from "react-i18next";
import { PageTitle } from "../components/PageTitle";

/** Show every step the app took, for finding out what went wrong. */
export function ActivityPage() {
  const { t } = useTranslation();
  const title = t("pages.activity.title");
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
    </>
  );
}
