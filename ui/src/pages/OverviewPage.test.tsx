import { act, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Overview } from "../api/types";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply, requestsTo } from "../test/backend";
import { step } from "../test/liveSocket";
import { overview } from "../test/overview";
import { runSummary } from "../test/runs";

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
      paths.bookings,
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

describe("OverviewPage while a run goes on", () => {
  it.each([
    ["scheduled", "Đang đặt sân theo hẹn giờ 06:00"],
    ["dry_run", "Đang chạy thử"],
    ["manual", "Đang đặt sân (chạy thủ công)"],
    ["setup", "Đang thiết lập tự động"],
  ])("names a %s run in a banner and says what waits for it", async (trigger, words) => {
    renderOverview(overview({ running: { trigger, pid: 4242, since: "05:50:02" } }));

    // The stub's "Đang tải…" is a status too: find the banner by its words.
    const locked = await screen.findByText(
      "Chạy thử và Thiết lập tự động tạm khóa cho tới khi xong",
    );
    const banner = locked.closest('[role="status"]');
    expect(banner).toHaveTextContent(words);
  });

  it("shows no banner while nothing runs", async () => {
    renderOverview(overview());

    await screen.findByRole("region", { name: "Lần đặt tiếp theo" });
    expect(screen.queryByText(/tạm khóa/)).not.toBeInTheDocument();
  });
});

describe("OverviewPage live run", () => {
  const SLOTS = ["15:00 - 16:00", "16:00 - 17:00"];
  /** The 06:00 run so far: started, waited, booking the first slot. */
  const STEPS = [
    step(101, {
      run_id: 30,
      time: "2026-10-15T05:50:02.200",
      kind: "run_started",
      data: { trigger: "scheduled", slots: SLOTS, dry_run: false },
    }),
    step(102, {
      run_id: 30,
      time: "2026-10-15T06:00:00.004",
      kind: "booking_started",
      data: { date: "2026-10-17", court: "S6 - Sân tennis" },
    }),
    step(103, {
      run_id: 30,
      time: "2026-10-15T06:00:00.010",
      kind: "slot_started",
      data: { slot: SLOTS[0], round: 1, rounds: 2 },
    }),
  ];
  const RUNNING = runSummary(30, {
    status: "running",
    finished_at: null,
    booked: 0,
    total: 0,
    slots: [],
  });

  function renderLive() {
    return renderApp(paths.overview, {
      "GET /api/status": reply(
        overview({
          running: { trigger: "scheduled", pid: 4242, since: "2026-10-15T05:50:01.900" },
          last_run: RUNNING,
        }),
      ),
      "GET /api/runs/30": reply({ ...RUNNING, steps: STEPS, log_lines: [] }),
    });
  }

  it("shows the run as it goes in place of the next and last booking", async () => {
    renderLive();

    const live = await screen.findByRole("region", {
      name: "Đang đặt cho Thứ Bảy 17/10 · sân S6",
    });
    expect(within(live).getByText("15:00–16:00")).toBeInTheDocument();
    const newest = within(live).getByRole("listitem", { current: "step" });
    expect(newest).toHaveTextContent("Lượt 1/2: 15:00–16:00đang chạy");
    expect(within(live).getByText("16:00–17:00 · chờ tới lượt")).toBeInTheDocument();
    expect(within(live).getByText("0/2")).toBeInTheDocument();
    expect(within(live).getByText("khung giờ đã đặt xong")).toBeInTheDocument();
    expect(within(live).getByRole("link", { name: "Xem nhật ký trực tiếp →" })).toHaveAttribute(
      "href",
      "/history/activity?run=30",
    );
    expect(screen.getByText(/Bạn có thể đóng cửa sổ này/)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Lần đặt tiếp theo" })).not.toBeInTheDocument();
  });

  it("follows the live feed and asks the backend only when a slot ends", async () => {
    const { live, fetch } = renderLive();
    await screen.findByText("0/2");
    const status = requestsTo(fetch, "GET /api/status");

    act(() => {
      live.current().open();
      live.current().send(step(104, { run_id: 30, kind: "calendar_opened", data: { attempt: 1 } }));
    });
    expect(await screen.findByText("Đã mở lịch đặt sân")).toBeInTheDocument();
    expect(requestsTo(fetch, "GET /api/status")).toBe(status);

    act(() => {
      live.current().send(
        step(105, {
          run_id: 30,
          kind: "slot_booked",
          category: "slot",
          data: { slot: SLOTS[0], seconds: 6, dry_run: false },
        }),
      );
    });
    expect(await screen.findByText("1/2")).toBeInTheDocument();
    expect(requestsTo(fetch, "GET /api/runs/30")).toBe(1);
    expect(requestsTo(fetch, "GET /api/status")).toBe(status + 1);
  });

  it("shows the run that just ended until it lets go of the lock", async () => {
    const ended = { ...RUNNING, status: "ok", booked: 2, total: 2 };
    const finished = step(110, {
      run_id: 30,
      time: "2026-10-15T06:00:12.000",
      kind: "run_finished",
      data: { status: "ok", booked: 2, total: 2 },
    });
    renderApp(paths.overview, {
      "GET /api/status": reply(
        overview({
          running: { trigger: "scheduled", pid: 4242, since: "2026-10-15T05:50:01.900" },
          last_run: ended,
        }),
      ),
      "GET /api/runs/30": reply({ ...ended, steps: [...STEPS, finished], log_lines: [] }),
    });

    const live = await screen.findByRole("region", {
      name: "Đang đặt cho Thứ Bảy 17/10 · sân S6",
    });
    expect(await within(live).findByText("Xong: 2/2 khung thành công")).toBeInTheDocument();
    expect(within(live).queryByRole("listitem", { current: "step" })).not.toBeInTheDocument();
  });

  it("does not take the run before the lock for the one holding it", async () => {
    const before = runSummary(29, { started_at: "2026-10-14T06:00:00.000" });
    renderApp(paths.overview, {
      "GET /api/status": reply(
        overview({
          running: { trigger: "dry_run", pid: 4242, since: "2026-10-15T10:00:00.000" },
          last_run: before,
        }),
      ),
    });

    expect(await screen.findByRole("region", { name: "Đang chuẩn bị" })).toBeInTheDocument();
  });

  it("gets ready while a dry run the app started has no step yet", async () => {
    renderApp(paths.overview, {
      "GET /api/status": reply(
        overview({ running: { trigger: "dry_run", pid: 4242, since: null } }),
      ),
    });

    expect(await screen.findByRole("region", { name: "Đang chuẩn bị" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Xem nhật ký trực tiếp →" })).not.toBeInTheDocument();
  });

  it("keeps the usual Overview under the banner during auto setup", async () => {
    renderOverview(overview({ running: { trigger: "setup", pid: 4242, since: "21:00:00" } }));

    expect(await screen.findByText("Đang thiết lập tự động")).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Lần đặt tiếp theo" })).toBeInTheDocument();
  });
});

describe("OverviewPage on an app not used yet", () => {
  /** No dry run has passed and the schedule is off. */
  function unused(fields: Partial<Overview> = {}): Overview {
    const status = overview();
    return overview({
      schedule: { ...status.schedule, enabled: false, dry_run_passed: false },
      ...fields,
    });
  }

  it("opens the welcome screen in its place", async () => {
    const { router } = renderOverview(unused());

    expect(await screen.findByRole("navigation", { name: "Các bước bắt đầu" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(paths.welcome);
    // Replaced, so going back does not land on the Overview and send the user on again.
    expect(router.state.historyAction).toBe("REPLACE");
  });

  it("sends the user there only once per opening", async () => {
    const { router } = renderOverview(unused());
    await screen.findByRole("navigation", { name: "Các bước bắt đầu" });

    await act(() => router.navigate(paths.overview));

    expect(await screen.findByRole("heading", { level: 1, name: "Tổng quan" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(paths.overview);
  });

  it("stays on the Overview once a dry run has passed", async () => {
    const status = unused();
    const { router } = renderOverview({
      ...status,
      schedule: { ...status.schedule, dry_run_passed: true },
    });

    expect(await statusLine()).toHaveTextContent("Bật hẹn giờ");
    expect(router.state.location.pathname).toBe(paths.overview);
  });

  it("leaves a run going on in view", async () => {
    const { router } = renderOverview(
      unused({ running: { trigger: "setup", pid: 4242, since: "2026-10-15T09:12:00.000" } }),
    );

    await screen.findByText("Đang thiết lập tự động");
    expect(router.state.location.pathname).toBe(paths.overview);
  });
});
