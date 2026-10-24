import { Navigate, type RouteObject } from "react-router";
import { App } from "./App";
import { Redirect } from "./components/Redirect";
import { BookingSettingsPage } from "./pages/BookingSettingsPage";
import { DeviceSetupPage } from "./pages/DeviceSetupPage";
import { ErrorPage } from "./pages/ErrorPage";
import { GuidePage } from "./pages/GuidePage";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { NotificationSettingsPage } from "./pages/NotificationSettingsPage";
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
      { index: true, element: <HomePage /> },
      { path: paths.schedule, element: <SchedulePage /> },
      // The addresses of History and Activity before they joined the home screen; a
      // `?run=` there opens that run beside the next booking.
      { path: "/history/*", element: <Redirect to={paths.overview} /> },
      { path: "/activity", element: <Redirect to={paths.overview} /> },
      {
        path: paths.settings,
        element: <SettingsPage />,
        children: [
          // Settings opens on its first tab.
          { index: true, element: <Navigate to={paths.bookingSettings} replace /> },
          { path: paths.bookingSettings, element: <BookingSettingsPage /> },
          { path: paths.deviceSetup, element: <DeviceSetupPage /> },
          { path: paths.notificationSettings, element: <NotificationSettingsPage /> },
        ],
      },
      { path: paths.guide, element: <GuidePage /> },
      { path: paths.welcome, element: <WelcomePage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
