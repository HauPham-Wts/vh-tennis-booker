import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { EmptyState, ErrorNotice, Loading } from "./States";

interface QueryViewProps<T> {
  query: UseQueryResult<T>;
  /** Decides when the data counts as nothing to show, such as an empty list. */
  isEmpty?: (data: T) => boolean;
  /** What to say then. */
  empty?: ReactNode;
  children: (data: T) => ReactNode;
}

/**
 * Show a read from the backend: its data once there, else the error with "Thử lại", else
 * that it is loading. Data already shown stays when a later refresh fails: an older view
 * helps more than an error.
 */
export function QueryView<T>({ query, isEmpty, empty, children }: QueryViewProps<T>) {
  if (query.data !== undefined) {
    if (isEmpty?.(query.data)) {
      return <EmptyState>{empty}</EmptyState>;
    }
    return children(query.data);
  }
  if (query.isError) {
    return <ErrorNotice error={query.error} onRetry={() => void query.refetch()} />;
  }
  return <Loading />;
}
