import { Outlet } from "react-router";

/** Lay out every screen: the current one fills the main area. */
export function App() {
  return (
    <main>
      <Outlet />
    </main>
  );
}
