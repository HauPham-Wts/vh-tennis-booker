import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { PageTitle } from "../components/PageTitle";
import { paths } from "../paths";

/** Tell the user that no screen has this address. */
export function NotFoundPage() {
  const { t } = useTranslation();
  const title = t("pages.notFound.title");
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
      <p>
        <Link to={paths.overview}>{t("pages.notFound.back")}</Link>
      </p>
    </>
  );
}
