import type { ReactNode } from "react";
import styles from "./PageHeader.module.css";
import { PageTitle } from "./PageTitle";

interface PageHeaderProps {
  /** The screen's name: the page heading and the window title. */
  title: string;
  /** One line under the title, such as what the screen is for. */
  lead?: ReactNode;
  /** Controls on the right, such as filters; they move under the title when narrow. */
  children?: ReactNode;
}

/** The top of a screen: its large title, a lead line and the screen's own controls. */
export function PageHeader({ title, lead, children }: PageHeaderProps) {
  return (
    <div className={styles.header}>
      <PageTitle>{title}</PageTitle>
      <div className={styles.text}>
        <h1 className={styles.title}>{title}</h1>
        {lead !== undefined && <p className={styles.lead}>{lead}</p>}
      </div>
      {children !== undefined && <div className={styles.actions}>{children}</div>}
    </div>
  );
}
