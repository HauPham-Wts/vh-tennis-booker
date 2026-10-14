import { Link } from "react-router";
import { paths } from "../paths";

/** Tell the user that no screen has this address. */
export function NotFoundPage() {
  return (
    <>
      <h1>Không tìm thấy trang</h1>
      <p>
        <Link to={paths.overview}>Về Tổng quan</Link>
      </p>
    </>
  );
}
