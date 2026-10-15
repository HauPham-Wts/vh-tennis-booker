import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { PageTitle } from "../components/PageTitle";
import { markWelcomeShown } from "../welcome";

/** Walk a first-time user through setup, settings and the schedule. */
export function WelcomePage() {
  const { t } = useTranslation();
  const title = t("pages.welcome.title");
  // Once seen, the Overview stops sending the user here until the app opens again.
  useEffect(markWelcomeShown, []);
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
    </>
  );
}
