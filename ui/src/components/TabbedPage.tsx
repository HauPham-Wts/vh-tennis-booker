import { NavLink, Outlet } from "react-router";
import { PageHeader } from "./PageHeader";
import styles from "./TabbedPage.module.css";

interface TabbedPageProps {
  /** The screen's name: the page heading and the window title. */
  title: string;
  /** The name of the row of tabs, for screen readers. */
  label: string;
  /** Each part of the screen: its address and the name on its tab. */
  tabs: readonly { to: string; label: string }[];
}

/**
 * Show a screen made of parts, one tab each, and the current part under the tabs. The tabs
 * are links, so each part keeps its address and the current one is marked with
 * aria-current="page".
 */
export function TabbedPage({ title, label, tabs }: TabbedPageProps) {
  return (
    <>
      <div className={styles.top}>
        <PageHeader title={title} />
        <nav aria-label={label} className={styles.tabs}>
          {tabs.map((tab) => (
            <NavLink key={tab.to} to={tab.to} className={styles.tab}>
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <Outlet />
    </>
  );
}
