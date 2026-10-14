import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Overview } from "../api/types";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply } from "../test/backend";

/** Everything ready for tomorrow's 06:00, as GET /api/status gives it. */
function overview(fields: Partial<Overview> = {}): Overview {
  return {
    version: "0.6.0",
    running: null,
    schedule: {
      enabled: true,
      wake_at: "05:50",
      start_at: "06:00",
      next_start: "2026-10-16T06:00",
      next_play_date: "2026-10-18",
      dry_run_passed: true,
    },
    last_run: null,
    setup: { checked_at: "2026-10-14T21:00:00.000", left: [] },
    ...fields,
  };
}

/** The booking settings, as far as the Overview reads them. */
const SETTINGS = { court: "S6 - Sân tennis", slots: ["15:00 - 16:00", "16:00 - 17:00"] };

function renderOverview(status: Overview) {
  return renderApp(paths.overview, {
    "GET /api/status": reply(status),
    "GET /api/settings": reply(SETTINGS),
  });
}

/** The status line beside the title. */
async function statusLine() {
  const heading = await screen.findByRole("heading", { level: 1, name: "Tổng quan" });
  const header = heading.parentElement?.parentElement as HTMLElement;
  return within(header).findByRole("link");
}

beforeEach(() => {
  // "Tomorrow" is 16/10: the page reads today from the clock.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 15, 0, 30));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("OverviewPage status line", () => {
  it("says everything is ready for the next start", async () => {
    renderOverview(overview());

    const link = await statusLine();
    expect(link.parentElement).toHaveTextContent("Mọi thứ đã sẵn sàng cho 06:00 sáng mai");
    expect(link).toHaveTextContent("Kiểm tra máy");
    expect(link).toHaveAttribute("href", paths.deviceSetup);
  });

  it("asks to set up the device when auto setup never ran", async () => {
    renderOverview(overview({ setup: null }));

    const link = await statusLine();
    expect(link.parentElement).toHaveTextContent("Chưa thiết lập máy");
    expect(link).toHaveTextContent("Thiết lập máy");
  });

  it("counts the setup items left", async () => {
    renderOverview(
      overview({
        setup: { checked_at: "2026-10-14T21:00:00.000", left: ["app_installed", "mumu_screen"] },
      }),
    );

    const link = await statusLine();
    expect(link.parentElement).toHaveTextContent("Còn 2 mục thiết lập máy cần làm");
    expect(link).toHaveAttribute("href", paths.deviceSetup);
  });

  it("asks to turn the schedule on", async () => {
    const status = overview();
    renderOverview({ ...status, schedule: { ...status.schedule, enabled: false } });

    const link = await statusLine();
    expect(link.parentElement).toHaveTextContent("Hẹn giờ đang tắt");
    expect(link).toHaveTextContent("Bật hẹn giờ");
    expect(link).toHaveAttribute("href", paths.schedule);
  });
});

describe("OverviewPage next booking", () => {
  it("shows the next start, when the PC wakes and what it will book", async () => {
    renderOverview(overview());

    const ticket = await screen.findByRole("region", { name: "Lần đặt tiếp theo" });
    expect(within(ticket).getByText("06:00")).toBeInTheDocument();
    expect(
      within(ticket).getByText("sáng Thứ Sáu 16/10 · đánh thức máy lúc 05:50"),
    ).toBeInTheDocument();
    const facts = await within(ticket).findAllByRole("definition");
    expect(facts.map((fact) => fact.textContent)).toEqual([
      "Chủ Nhật 18/10",
      "S6",
      "15:00–16:00",
      "16:00–17:00",
    ]);
  });

  it("still says what would be booked with the schedule off, and how to turn it on", async () => {
    const status = overview();
    renderOverview({ ...status, schedule: { ...status.schedule, enabled: false } });

    const ticket = await screen.findByRole("region", { name: "Hẹn giờ đang tắt" });
    expect(
      within(ticket).getByText(/Bật hẹn giờ để app tự đặt lúc 06:00 mỗi sáng/),
    ).toBeInTheDocument();
    expect(within(ticket).getByRole("link", { name: "Bật hẹn giờ" })).toHaveAttribute(
      "href",
      paths.schedule,
    );
    expect(await within(ticket).findByText("Chủ Nhật 18/10")).toBeInTheDocument();
  });
});
