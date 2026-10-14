import { useTranslation } from "react-i18next";
import { PageTitle } from "../components/PageTitle";

/** Explain each screen and what to do when something fails. */
export function GuidePage() {
  const { t } = useTranslation();
  const title = t("pages.guide.title");
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
    </>
  );
}
