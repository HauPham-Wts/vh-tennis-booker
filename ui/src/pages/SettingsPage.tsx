import { Outlet } from "react-router";

/** Hold the booking settings and the device setup, one tab each. */
export function SettingsPage() {
  return (
    <>
      <h1>Cài đặt</h1>
      <Outlet />
    </>
  );
}
