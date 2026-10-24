import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import { paths } from "./paths";
import { stubBackend } from "./test/backend";
import { createTestQueryClient } from "./test/queries";

/**
 * Render the layout at `path` with a stand-in screen for the home screen; the header's
 * status line and language switch need a cache, and the backend answers nothing.
 */
function renderAt(path: string) {
  stubBackend({});
  const router = createMemoryRouter(
    [
      {
        path: paths.overview,
        element: <App />,
        children: [{ index: true, element: <p>Home screen</p> }],
      },
    ],
    { initialEntries: [path] },
  );
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("App", () => {
  it("shows the current screen inside the main area", () => {
    renderAt(paths.overview);

    expect(within(screen.getByRole("main")).getByText("Home screen")).toBeInTheDocument();
  });

  it("shows the name and the language switch in the header, and no menu", () => {
    renderAt(paths.overview);

    const header = screen.getByRole("banner");
    expect(header).toHaveTextContent("court booker");
    expect(within(header).getByRole("group", { name: "Ngôn ngữ" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("starts with a link that skips to the main area", () => {
    renderAt(paths.overview);

    const [first] = screen.getAllByRole("link");
    expect(first).toHaveTextContent("Bỏ qua tới nội dung");
    expect(first).toHaveAttribute("href", "#main");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
  });
});
