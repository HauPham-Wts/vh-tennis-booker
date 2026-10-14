import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply } from "../test/backend";
import { runSummary } from "../test/runs";

const RUNS = [
  runSummary(26),
  runSummary(25, {
    trigger: "dry_run",
    dry_run: true,
    started_at: "2026-10-14T19:43:00.000",
    status: "failed",
    booked: 0,
    total: 1,
  }),
  runSummary(24, { trigger: "manual", started_at: "2026-10-14T08:32:16.966", status: "running" }),
];

describe("ActivityPage", () => {
  it("lists the recent runs with their result and shows the newest", async () => {
    const { fetch } = renderApp(paths.activity, { "GET /api/runs": reply(RUNS) });

    const list = await screen.findByRole("navigation", { name: "Các lần chạy" });
    const links = within(list).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([
      "15/10 05:50 · hẹn giờ✓ 2/2",
      "14/10 19:43 · chạy thử✕ 0/1",
      "14/10 08:32 · thủ công…",
    ]);
    expect(links[0]).toHaveAttribute("aria-current", "true");
    expect(links[1]).not.toHaveAttribute("aria-current");
    expect(new URL(fetch.mock.calls[0]![0].url).searchParams.get("limit")).toBe("30");
  });

  it("shows the run asked for in the address", async () => {
    renderApp(`${paths.activity}?run=25`, { "GET /api/runs": reply(RUNS) });

    const list = await screen.findByRole("navigation", { name: "Các lần chạy" });
    expect(within(list).getByRole("link", { current: true })).toHaveTextContent("chạy thử");
  });

  it("says when there is no run yet", async () => {
    renderApp(paths.activity, { "GET /api/runs": reply([]) });

    expect(await screen.findByText("Chưa có lần chạy nào.")).toBeInTheDocument();
  });
});
