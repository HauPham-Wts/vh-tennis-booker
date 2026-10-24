import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";
import { paths } from "../paths";
import styles from "./MainNav.module.css";

/** The screens in the navigation; the History is part of the overview. */
const ITEMS = [
  { to: paths.overview, label: "nav.overview" },
  { to: paths.schedule, label: "nav.schedule" },
  { to: paths.settings, label: "nav.settings" },
  { to: paths.guide, label: "nav.guide" },
] as const;

/** Link every screen; NavLink marks the current one with aria-current="page". */
export function MainNav() {
  const { t } = useTranslation();
  return (
    <nav aria-label={t("nav.label")}>
      <ul className={styles.list}>
        {ITEMS.map(({ to, label }) => (
          <li key={to}>
            {/* NavLink treats "/" as current on the overview only, not on every address. */}
            <NavLink to={to} className={styles.link}>
              {t(label)}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
