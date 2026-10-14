import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, type RouteObject, RouterProvider } from "react-router";
import { LiveProvider } from "../api/LiveProvider";
import { routes } from "../routes";
import { type Reply, stubBackend } from "./backend";
import { fakeConnection } from "./liveSocket";
import { createTestQueryClient } from "./queries";

/**
 * Render the app at `path` as main.tsx does: a cache of its own, the live feed on fake
 * sockets and a stand-in backend answering `replies` (other requests get not_found).
 */
export function renderApp(
  path: string,
  replies: Record<string, Reply> = {},
  table: RouteObject[] = routes,
) {
  const fetch = stubBackend(replies);
  const live = fakeConnection();
  const cache = createTestQueryClient();
  const router = createMemoryRouter(table, { initialEntries: [path] });
  const view = render(
    <QueryClientProvider client={cache}>
      <LiveProvider connection={live.connection}>
        <RouterProvider router={router} />
      </LiveProvider>
    </QueryClientProvider>,
  );
  return { router, fetch, live, cache, view };
}
