import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { STORAGE_KEY } from "../i18n";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply, requestsTo } from "../test/backend";

/** Render the whole app on the home screen. */
function renderHome() {
  renderApp(paths.overview);
}

describe("LanguageSwitch", () => {
  it("names each language in itself and presses the one in use", () => {
    renderHome();

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
    renderHome();

    fireEvent.click(screen.getByRole("button", { name: "EN English" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "History" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "EN English" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await waitFor(() => expect(document.title).toBe("Overview · Court Booker"));
    expect(document.documentElement.lang).toBe("en");
    expect(localStorage.getItem(STORAGE_KEY)).toBe("en");
  });

  it("switches back to Vietnamese", async () => {
    renderHome();

    fireEvent.click(screen.getByRole("button", { name: "EN English" }));
    await screen.findByRole("heading", { level: 1, name: "Overview" });
    fireEvent.click(screen.getByRole("button", { name: "VI Tiếng Việt" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Tổng quan" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("vi");
    expect(localStorage.getItem(STORAGE_KEY)).toBe("vi");
  });

  it("gives the Windows notification the language chosen", async () => {
    const { fetch } = renderApp(paths.overview, {
      "GET /api/notifications": reply({ enabled: false, language: "vi" }),
      "PUT /api/notifications": reply({ enabled: false, language: "en" }),
    });

    fireEvent.click(screen.getByRole("button", { name: "EN English" }));

    await waitFor(() => expect(requestsTo(fetch, "PUT /api/notifications")).toBe(1));
    const put = fetch.mock.calls.map(([request]) => request).find((r) => r.method === "PUT");
    expect(await put?.json()).toEqual({ enabled: false, language: "en" });
  });

  it("saves nothing when the notification has that language already", async () => {
    const { fetch } = renderApp(paths.overview, {
      "GET /api/notifications": reply({ enabled: true, language: "vi" }),
    });

    fireEvent.click(screen.getByRole("button", { name: "VI Tiếng Việt" }));

    await waitFor(() => expect(requestsTo(fetch, "GET /api/notifications")).toBe(1));
    expect(requestsTo(fetch, "PUT /api/notifications")).toBe(0);
  });

  it("switches the UI even when the notification cannot be saved", async () => {
    renderApp(paths.overview, {
      "GET /api/notifications": reply({ error: "engine", detail: "broken" }, 500),
    });

    fireEvent.click(screen.getByRole("button", { name: "EN English" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Overview" })).toBeInTheDocument();
  });
});
