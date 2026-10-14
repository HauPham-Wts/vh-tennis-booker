import { NavLink } from "react-router";
import { paths } from "../paths";
import styles from "./MainNav.module.css";

/** The screens in the navigation, in the order of the mockups. */
const ITEMS = [
  { to: paths.overview, label: "Tổng quan" },
  { to: paths.schedule, label: "Hẹn giờ" },
  { to: paths.history, label: "Lịch sử" },
  { to: paths.activity, label: "Nhật ký" },
  { to: paths.settings, label: "Cài đặt" },
  { to: paths.guide, label: "Hướng dẫn" },
] as const;

/** Link every screen; NavLink marks the current one with aria-current="page". */
export function MainNav() {
  return (
    <nav aria-label="Điều hướng chính">
      <ul className={styles.list}>
        {ITEMS.map(({ to, label }) => (
          <li key={to}>
            {/* "end" keeps the overview from matching every address under "/". */}
            <NavLink to={to} end={to === paths.overview} className={styles.link}>
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
