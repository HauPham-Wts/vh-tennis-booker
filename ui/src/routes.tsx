import { Navigate, type RouteObject } from "react-router";
import { App } from "./App";
import { ActivityPage } from "./pages/ActivityPage";
import { BookingSettingsPage } from "./pages/BookingSettingsPage";
import { DeviceSetupPage } from "./pages/DeviceSetupPage";
import { ErrorPage } from "./pages/ErrorPage";
import { GuidePage } from "./pages/GuidePage";
import { HistoryPage } from "./pages/HistoryPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OverviewPage } from "./pages/OverviewPage";
import { SchedulePage } from "./pages/SchedulePage";
import { SettingsPage } from "./pages/SettingsPage";
import { WelcomePage } from "./pages/WelcomePage";
import { paths } from "./paths";

/** Every screen under the app's layout; shared by the browser router and the tests. */
export const routes: RouteObject[] = [
  {
    path: paths.overview,
    element: <App />,
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: paths.schedule, element: <SchedulePage /> },
      { path: paths.history, element: <HistoryPage /> },
      { path: paths.activity, element: <ActivityPage /> },
      {
        path: paths.settings,
        element: <SettingsPage />,
        children: [
          // Settings opens on its first tab.
          { index: true, element: <Navigate to={paths.bookingSettings} replace /> },
          { path: paths.bookingSettings, element: <BookingSettingsPage /> },
          { path: paths.deviceSetup, element: <DeviceSetupPage /> },
        ],
      },
      { path: paths.guide, element: <GuidePage /> },
      { path: paths.welcome, element: <WelcomePage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
