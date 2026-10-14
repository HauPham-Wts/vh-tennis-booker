import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { STORAGE_KEY } from "../i18n";
import { paths } from "../paths";
import { routes } from "../routes";

/** Render the whole app on the history screen. */
function renderHistory() {
  const router = createMemoryRouter(routes, { initialEntries: [paths.history] });
  render(<RouterProvider router={router} />);
}

describe("LanguageSwitch", () => {
  it("names each language in itself and presses the one in use", () => {
    renderHistory();

    const group = screen.getByRole("group", { name: "Ngôn ngữ" });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "VI Tiếng Việt" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "EN English" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("switches the whole UI to English and remembers it", async () => {
    renderHistory();

    fireEvent.click(screen.getByRole("button", { name: "EN English" }));

    expect(await screen.findByRole("heading", { level: 1, name: "History" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "EN English" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await waitFor(() => expect(document.title).toBe("History · Court Booker"));
    expect(document.documentElement.lang).toBe("en");
    expect(localStorage.getItem(STORAGE_KEY)).toBe("en");
  });

  it("switches back to Vietnamese", async () => {
    renderHistory();

    fireEvent.click(screen.getByRole("button", { name: "EN English" }));
    await screen.findByRole("heading", { level: 1, name: "History" });
    fireEvent.click(screen.getByRole("button", { name: "VI Tiếng Việt" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Lịch sử" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("vi");
    expect(localStorage.getItem(STORAGE_KEY)).toBe("vi");
  });
});
