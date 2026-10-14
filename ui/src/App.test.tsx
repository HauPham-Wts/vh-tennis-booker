import { render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import { paths } from "./paths";

/** Render the layout at `path` with a stand-in screen for the overview and the welcome. */
function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      {
        path: paths.overview,
        element: <App />,
        children: [
          { index: true, element: <p>Overview screen</p> },
          { path: paths.welcome, element: <p>Welcome screen</p> },
        ],
      },
    ],
    { initialEntries: [path] },
  );
  render(<RouterProvider router={router} />);
}

describe("App", () => {
  it("shows the current screen inside the main area", () => {
    renderAt(paths.overview);

    expect(within(screen.getByRole("main")).getByText("Overview screen")).toBeInTheDocument();
  });

  it("shows the name and the navigation in the header", () => {
    renderAt(paths.overview);

    const header = screen.getByRole("banner");
    expect(header).toHaveTextContent("court booker");
    expect(
      within(header).getByRole("navigation", { name: "Điều hướng chính" }),
    ).toBeInTheDocument();
  });

  it("leaves the navigation out of the welcome screen", () => {
    renderAt(paths.welcome);

    expect(screen.getByRole("banner")).toHaveTextContent("court booker");
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(within(screen.getByRole("main")).getByText("Welcome screen")).toBeInTheDocument();
  });

  it("starts with a link that skips to the main area", () => {
    renderAt(paths.overview);

    const [first] = screen.getAllByRole("link");
    expect(first).toHaveTextContent("Bỏ qua tới nội dung");
    expect(first).toHaveAttribute("href", "#main");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
  });
});
