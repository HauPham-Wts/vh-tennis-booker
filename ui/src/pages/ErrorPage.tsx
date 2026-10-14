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
  const error = useRouteError();
  return (
    <main>
      <PageTitle>Có lỗi xảy ra</PageTitle>
      <h1>Có lỗi xảy ra</h1>
      <p>{describeError(error)}</p>
      <p>
        {/* A full reload starts the app afresh. */}
        <a href={paths.overview}>Mở lại Tổng quan</a>
      </p>
    </main>
  );
}
