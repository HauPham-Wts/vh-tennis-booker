import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { errorMessage } from "../api/errors";
import { Button } from "./Button";
import styles from "./States.module.css";

/** Say that data is on its way; screen readers hear it once. */
export function Loading() {
  const { t } = useTranslation();
  return (
    <p role="status" className={styles.quiet}>
      {t("common.loading")}
    </p>
  );
}

interface ErrorNoticeProps {
  error: unknown;
  /** Offers "Thử lại" when given. */
  onRetry?: () => void;
}

/** Say what went wrong in the current language, never a raw code. */
export function ErrorNotice({ error, onRetry }: ErrorNoticeProps) {
  const { t } = useTranslation();
  return (
    <div role="alert" className={styles.error}>
      <p className={styles.message}>{errorMessage(t, error)}</p>
      {onRetry !== undefined && <Button onClick={onRetry}>{t("common.retry")}</Button>}
    </div>
  );
}

/** Say that there is nothing to show yet, in the screen's own words. */
export function EmptyState({ children }: { children: ReactNode }) {
  return <p className={styles.quiet}>{children}</p>;
}
