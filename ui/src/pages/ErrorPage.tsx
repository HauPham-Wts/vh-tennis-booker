import { useTranslation } from "react-i18next";
import { isRouteErrorResponse, useRouteError } from "react-router";
import { PageTitle } from "../components/PageTitle";
import { paths } from "../paths";

/** Describe an error thrown while a screen rendered. */
function describeError(error: unknown): string {
  if (isRouteErrorResponse(error)) {
    return `${error.status} ${error.statusText}`;
  }
  return error instanceof Error ? error.message : String(error);
}

/** Replace a screen that failed with the error, instead of a blank window. */
export function ErrorPage() {
  const { t } = useTranslation();
  const error = useRouteError();
  const title = t("pages.error.title");
  return (
    <main>
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
      <p>{describeError(error)}</p>
      <p>
        {/* A full reload starts the app afresh. */}
        <a href={paths.overview}>{t("pages.error.reload")}</a>
      </p>
    </main>
  );
}
