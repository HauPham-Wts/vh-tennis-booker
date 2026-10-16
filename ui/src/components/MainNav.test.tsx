import { render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { paths } from "../paths";
import { MainNav } from "./MainNav";

/** Render the navigation as if the window showed `path`. */
function renderAt(path: string) {
  const router = createMemoryRouter([{ path: "*", element: <MainNav /> }], {
    initialEntries: [path],
  });
  render(<RouterProvider router={router} />);
}

/** Return the names of the links marked as the current page. */
function currentLinks(): string[] {
  return screen
    .getAllByRole("link")
    .filter((link) => link.getAttribute("aria-current") === "page")
    .map((link) => link.textContent ?? "");
}

describe("MainNav", () => {
  it("links every screen in the order of the mockups", () => {
    renderAt(paths.overview);

    const nav = screen.getByRole("navigation", { name: "Điều hướng chính" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["Tổng quan", paths.overview],
      ["Hẹn giờ", paths.schedule],
      ["Lịch sử", paths.history],
      ["Cài đặt", paths.settings],
      ["Hướng dẫn", paths.guide],
    ]);
  });

  it.each([
    [paths.overview, "Tổng quan"],
    [paths.schedule, "Hẹn giờ"],
    [paths.bookings, "Lịch sử"],
    [paths.activity, "Lịch sử"],
    [paths.bookingSettings, "Cài đặt"],
    [paths.deviceSetup, "Cài đặt"],
    [paths.guide, "Hướng dẫn"],
  ])("marks only one link as current on %s: %s", (path, current) => {
    renderAt(path);

    expect(currentLinks()).toEqual([current]);
  });

  it("marks no link on a screen outside the navigation", () => {
    renderAt(paths.welcome);

    expect(currentLinks()).toEqual([]);
  });
});
