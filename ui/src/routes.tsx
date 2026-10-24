import type { RouteObject } from "react-router";
import { App } from "./App";
import { Redirect } from "./components/Redirect";
import { ErrorPage } from "./pages/ErrorPage";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OLD_PATHS, paths } from "./paths";

/** Every screen under the app's layout; shared by the browser router and the tests. */
export const routes: RouteObject[] = [
  {
    path: paths.overview,
    element: <App />,
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <HomePage /> },
      ...OLD_PATHS.map((path) => ({ path, element: <Redirect to={paths.overview} /> })),
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
