import { act, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Overview } from "../api/types";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply, requestsTo } from "../test/backend";
import { step } from "../test/liveSocket";
import { overview } from "../test/overview";
import { runSummary } from "../test/runs";

/** The booking settings, as far as the home screen reads them. */
const SETTINGS = { court: "S6 - Sân tennis", slots: ["15:00 - 16:00", "16:00 - 17:00"] };

function renderOverview(status: Overview) {
  return renderApp(paths.overview, {
    "GET /api/status": reply(status),
    "GET /api/settings": reply(SETTINGS),
    "GET /api/runs": reply([]),
  });
}

/** The link of the status line in the header. */
async function statusLine() {
  // The navigation's links come first; the status line's is the last link of the header.
  await within(screen.getByRole("banner")).findByText(/●/);
  return within(screen.getByRole("banner")).getAllByRole("link").at(-1) as HTMLElement;
}

beforeEach(() => {
  // "Tomorrow" is 16/10: the page reads today from the clock.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 15, 0, 30));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("HomePage status line", () => {
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

describe("HomePage next booking", () => {
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

describe("HomePage while a run goes on", () => {
  it.each([
    ["scheduled", "Đang đặt sân theo hẹn giờ 06:00"],
    ["dry_run", "Đang chạy thử"],
    ["manual", "Đang đặt sân (chạy thủ công)"],
    ["setup", "Đang thiết lập tự động"],
  ])("names a %s run in the header and says what waits for it", async (trigger, words) => {
    renderOverview(overview({ running: { trigger, pid: 4242, since: "05:50:02" } }));

    const header = screen.getByRole("banner");
    expect(await within(header).findByRole("status")).toHaveTextContent(words);
    expect(
      screen.getByText("Chạy thử và Thiết lập tự động tạm khóa cho tới khi xong"),
    ).toBeInTheDocument();
  });

  it("says nothing is locked while nothing runs", async () => {
    renderOverview(overview());

    await screen.findByRole("region", { name: "Lần đặt tiếp theo" });
    expect(within(screen.getByRole("banner")).queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByText(/tạm khóa/)).not.toBeInTheDocument();
  });
});

describe("HomePage live run", () => {
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

  it("shows the run as it goes in place of the next booking", async () => {
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
  });

  it("keeps the next booking in view during auto setup", async () => {
    renderOverview(overview({ running: { trigger: "setup", pid: 4242, since: "21:00:00" } }));

    expect(await screen.findByText("Đang thiết lập tự động")).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Lần đặt tiếp theo" })).toBeInTheDocument();
  });
});

describe("HomePage on an app not used yet", () => {
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
    // Replaced, so going back does not land on the home screen and send the user on again.
    expect(router.state.historyAction).toBe("REPLACE");
  });

  it("sends the user there only once per opening", async () => {
    const { router } = renderOverview(unused());
    await screen.findByRole("navigation", { name: "Các bước bắt đầu" });

    await act(() => router.navigate(paths.overview));

    expect(await screen.findByRole("heading", { level: 1, name: "Tổng quan" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(paths.overview);
  });

  it("stays on the home screen once a dry run has passed", async () => {
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
