import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Overview } from "../api/types";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply } from "../test/backend";
import { runSummary } from "../test/runs";

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

function renderOverview(status: Overview, lastRuns: unknown[] = []) {
  return renderApp(paths.overview, {
    "GET /api/status": reply(status),
    "GET /api/settings": reply(SETTINGS),
    "GET /api/runs": reply(lastRuns),
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

describe("OverviewPage last booking", () => {
  /** This morning's booking: the first slot booked, the second full. */
  const LAST = runSummary(26, {
    status: "partial",
    booked: 1,
    slots: [
      {
        slot: "15:00 - 16:00",
        ok: true,
        reason: null,
        finished_at: "2026-10-15T06:00:06.120",
        seconds: 6,
        commands: 54,
      },
      {
        slot: "16:00 - 17:00",
        ok: false,
        reason: "Slot 16:00 - 17:00 is fully booked",
        finished_at: "2026-10-15T06:00:11.300",
        seconds: 4.3,
        commands: 30,
      },
    ],
  });

  it("shows the newest real booking, one card per slot", async () => {
    const { fetch } = renderOverview(overview(), [LAST]);

    const section = await screen.findByRole("region", {
      name: "Lần đặt gần nhất · sáng nay 15/10",
    });
    expect(within(section).getAllByText("ĐẶT ĐƯỢC 1/2")).toHaveLength(1);
    const cards = within(section).getAllByRole("article");
    expect(cards[0]).toHaveTextContent("15:00–16:00ĐÃ ĐẶT");
    expect(cards[0]).toHaveTextContent("Thứ Bảy 17/10 · sân S6");
    expect(cards[0]).toHaveTextContent("Đặt xong lúc 06:00:06 · mất 6,0 giây");
    expect(cards[1]).toHaveTextContent("16:00–17:00KHÔNG ĐẶT ĐƯỢC");
    expect(cards[1]).toHaveTextContent("Hết chỗ");
    expect(within(section).getByRole("link", { name: "Xem lịch sử →" })).toHaveAttribute(
      "href",
      paths.history,
    );
    const query = fetch.mock.calls
      .map(([request]) => new URL(request.url))
      .find(({ pathname }) => pathname === "/api/runs")?.searchParams;
    expect(query?.get("dry_run")).toBe("false");
    expect(query?.get("limit")).toBe("1");
  });

  it("says why a run stopped before any slot", async () => {
    const stopped = runSummary(27, {
      status: "failed",
      booked: 0,
      total: 0,
      slots: [],
      error: "Another run is in progress: dry_run run (pid 17156) since 05:49:12",
    });
    renderOverview(overview(), [stopped]);

    const section = await screen.findByRole("region", { name: /Lần đặt gần nhất/ });
    expect(within(section).getByText("KHÔNG ĐẶT ĐƯỢC")).toBeInTheDocument();
    expect(within(section).getByText("Đang có lần chạy khác")).toBeInTheDocument();
  });

  it("shows nothing before a first real booking", async () => {
    renderOverview(overview(), []);

    await screen.findByRole("region", { name: "Lần đặt tiếp theo" });
    expect(screen.queryByRole("region", { name: /Lần đặt gần nhất/ })).not.toBeInTheDocument();
  });
});
