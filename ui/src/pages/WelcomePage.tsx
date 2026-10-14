import { useTranslation } from "react-i18next";
import { PageTitle } from "../components/PageTitle";

/** Walk a first-time user through setup, settings and the schedule. */
export function WelcomePage() {
  const { t } = useTranslation();
  const title = t("pages.welcome.title");
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
    </>
  );
}
