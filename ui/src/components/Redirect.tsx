import { Navigate, useLocation } from "react-router";

/** Send the window on to `to`, keeping the query of the address (`?month=`, `?run=`). */
export function Redirect({ to }: { to: string }) {
  const { search } = useLocation();
  return <Navigate to={{ pathname: to, search }} replace />;
}
