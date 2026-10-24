import { screen, waitFor } from "@testing-library/react";
import type { RouteObject } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { paths } from "./paths";
import { routes } from "./routes";
import { renderApp } from "./test/app";

/** Render a route table at one address and return its router. */
function renderAt(path: string, table: RouteObject[] = routes) {
  return renderApp(path, {}, table).router;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("routes", () => {
  it("opens / on the home screen and names the window", async () => {
    renderAt(paths.overview);

    expect(await screen.findByRole("heading", { level: 1, name: "Tổng quan" })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe("Tổng quan · Court Booker"));
  });

  it.each([
    ["/history", paths.overview],
    ["/history/bookings?month=2026-09", `${paths.overview}?month=2026-09`],
    ["/history/activity?run=25", `${paths.overview}?run=25`],
    ["/activity?run=25", `${paths.overview}?run=25`],
    ["/schedule", paths.overview],
    ["/settings", paths.overview],
    ["/settings/booking", paths.overview],
    ["/settings/device", paths.overview],
    ["/settings/notifications", paths.overview],
    ["/guide", paths.overview],
    ["/welcome?step=2", `${paths.overview}?step=2`],
  ])("sends the old address %s on to %s", async (path, to) => {
    const router = renderAt(path);

    await screen.findByRole("tab", { name: /^Lịch sử/ });
    const { pathname, search } = router.state.location;
    expect(pathname + search).toBe(to);
    expect(router.state.historyAction).toBe("REPLACE");
  });

  it("shows the not-found page for an unknown address", async () => {
    renderAt("/no-such-screen");

    expect(
      await screen.findByRole("heading", { level: 1, name: "Không tìm thấy trang" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Về Tổng quan" })).toHaveAttribute(
      "href",
      paths.overview,
    );
  });

  it("replaces a screen that throws with the error page", async () => {
    // React reports the thrown error on the console; the page is what matters here.
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    function BrokenScreen(): never {
      throw new Error("The screen broke");
    }
    const [root] = routes;
    if (!root || root.index) {
      throw new Error("The route table must start with the layout route");
    }
    const table: RouteObject[] = [
      { ...root, children: [{ index: true, element: <BrokenScreen /> }] },
    ];

    renderAt(paths.overview, table);

    expect(
      await screen.findByRole("heading", { level: 1, name: "Có lỗi xảy ra" }),
    ).toBeInTheDocument();
    expect(screen.getByText("The screen broke")).toBeInTheDocument();
  });
});
