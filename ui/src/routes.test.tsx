import { screen, waitFor, within } from "@testing-library/react";
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
  it.each([
    [paths.overview, "Tổng quan"],
    [paths.schedule, "Hẹn giờ"],
    [paths.guide, "Hướng dẫn"],
  ])("opens %s on the %s screen and names the window", async (path, title) => {
    renderAt(path);

    expect(await screen.findByRole("heading", { level: 1, name: title })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe(`${title} · Court Booker`));
  });

  it("opens /welcome on its steps and names the window", async () => {
    renderAt(paths.welcome);

    expect(await screen.findByRole("navigation", { name: "Các bước bắt đầu" })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe("Chào mừng · Court Booker"));
  });

  it.each([
    [paths.bookingSettings, "Đặt sân"],
    [paths.deviceSetup, "Thiết lập máy"],
  ])("opens %s as the %s tab of the settings", async (path, tab) => {
    renderAt(path);

    expect(await screen.findByRole("heading", { level: 1, name: "Cài đặt" })).toBeInTheDocument();
    const tabs = screen.getByRole("navigation", { name: "Phần cài đặt" });
    expect(within(tabs).getByRole("link", { name: tab })).toHaveAttribute("aria-current", "page");
    await waitFor(() => expect(document.title).toBe("Cài đặt · Court Booker"));
  });

  it.each([
    [paths.bookings, "Lịch sử"],
    [paths.activity, "Nhật ký"],
  ])("opens %s as the %s tab of the history", async (path, tab) => {
    renderAt(path);

    expect(await screen.findByRole("heading", { level: 1, name: "Lịch sử" })).toBeInTheDocument();
    const tabs = screen.getByRole("navigation", { name: "Phần lịch sử" });
    expect(within(tabs).getByRole("link", { name: tab })).toHaveAttribute("aria-current", "page");
    await waitFor(() => expect(document.title).toBe("Lịch sử · Court Booker"));
  });

  it.each([
    [`${paths.history}?month=2026-09`, `${paths.bookings}?month=2026-09`],
    ["/activity?run=25", `${paths.activity}?run=25`],
  ])("sends %s on to %s", async (path, to) => {
    const router = renderAt(path);

    await screen.findByRole("navigation", { name: "Phần lịch sử" });
    const { pathname, search } = router.state.location;
    expect(pathname + search).toBe(to);
    expect(router.state.historyAction).toBe("REPLACE");
  });

  it("opens the settings on the booking tab", async () => {
    const router = renderAt(paths.settings);

    const tabs = await screen.findByRole("navigation", { name: "Phần cài đặt" });
    expect(within(tabs).getByRole("link", { name: "Đặt sân" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(router.state.location.pathname).toBe(paths.bookingSettings);
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
