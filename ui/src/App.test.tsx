import { render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("shows the current screen inside the main area", () => {
    const router = createMemoryRouter([
      { path: "/", element: <App />, children: [{ index: true, element: <p>Screen</p> }] },
    ]);

    render(<RouterProvider router={router} />);

    expect(within(screen.getByRole("main")).getByText("Screen")).toBeInTheDocument();
  });
});
