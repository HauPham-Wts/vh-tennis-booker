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
  it.each([
    [paths.overview, "Tổng quan"],
    [paths.schedule, "Hẹn giờ"],
    [paths.history, "Lịch sử"],
    [paths.activity, "Nhật ký"],
    [paths.guide, "Hướng dẫn"],
    [paths.welcome, "Chào mừng"],
  ])("opens %s on the %s screen and names the window", async (path, title) => {
    renderAt(path);

    expect(await screen.findByRole("heading", { level: 1, name: title })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe(`${title} · Court Booker`));
  });

  it.each([
    [paths.bookingSettings, "Đặt sân"],
    [paths.deviceSetup, "Thiết lập máy"],
  ])("opens %s as the %s tab of the settings", async (path, tab) => {
    renderAt(path);

    expect(await screen.findByRole("heading", { level: 1, name: "Cài đặt" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: tab })).toBeInTheDocument();
  });

  it("opens the settings on the booking tab", async () => {
    const router = renderAt(paths.settings);

    expect(await screen.findByRole("heading", { level: 2, name: "Đặt sân" })).toBeInTheDocument();
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
