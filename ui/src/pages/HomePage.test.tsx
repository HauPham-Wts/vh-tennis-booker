import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Overview } from "../api/types";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply, requestsTo } from "../test/backend";
import { step } from "../test/liveSocket";
import { overview } from "../test/overview";
import { runSummary } from "../test/runs";
import { settings } from "../test/settings";
import { STORAGE_KEY } from "../manualSteps";

function renderOverview(status: Overview) {
  return renderApp(paths.overview, {
    "GET /api/status": reply(status),
    "GET /api/settings": reply(settings()),
    "GET /api/runs": reply([]),
  });
}

/** The status line in the header. */
async function statusLine() {
  const dot = await within(screen.getByRole("banner")).findByText(/●/);
  return dot.closest("p") as HTMLElement;
}

/** Tick the setup steps only the user can do. */
function tickSteps(done = { mumu: true, app: true, login: true }) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(done));
}

beforeEach(() => {
  tickSteps();
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

    const line = await statusLine();
    expect(line).toHaveTextContent("Sẵn sàng cho 06:00 sáng mai");
    expect(within(line).queryByRole("link")).not.toBeInTheDocument();
  });

  it("counts auto setup that never ran as a setup task", async () => {
    renderOverview(overview({ setup: null }));

    expect(await statusLine()).toHaveTextContent("Còn 1 việc thiết lập, xem khung bên phải");
  });

  it("counts the steps not ticked and auto setup left, before anything else", async () => {
    tickSteps({ mumu: true, app: false, login: true });
    const status = overview({
      setup: { checked_at: "2026-10-14T21:00:00.000", left: ["app_installed", "mumu_screen"] },
    });
    renderOverview({
      ...status,
      schedule: { ...status.schedule, enabled: false, dry_run_passed: false },
    });

    expect(await statusLine()).toHaveTextContent("Còn 2 việc thiết lập, xem khung bên phải");
  });

  it("asks for a dry run before the daily switch", async () => {
    const status = overview();
    renderOverview({
      ...status,
      schedule: { ...status.schedule, enabled: true, dry_run_passed: false },
    });

    expect(await statusLine()).toHaveTextContent("Chưa chạy thử đạt · bấm Chạy thử ngay");
  });

  it("asks to turn the daily booking on once a dry run passed", async () => {
    const status = overview();
    renderOverview({ ...status, schedule: { ...status.schedule, enabled: false } });

    expect(await statusLine()).toHaveTextContent("Chạy thử đạt · bật Tự đặt");
  });
});

describe("HomePage while a run goes on", () => {
  it.each([
    ["scheduled", "Đang đặt sân theo hẹn giờ 06:00"],
    ["dry_run", "Đang chạy thử"],
    ["manual", "Đang đặt sân (chạy thủ công)"],
    ["setup", "Đang thiết lập tự động"],
  ])("names a %s run in the header", async (trigger, words) => {
    renderOverview(overview({ running: { trigger, pid: 4242, since: "05:50:02", runs: [] } }));

    const header = screen.getByRole("banner");
    expect(await within(header).findByRole("status")).toHaveTextContent(words);
  });

  it("shows no run while nothing runs", async () => {
    renderOverview(overview());

    await screen.findByRole("region", { name: "Lần đặt tiếp theo" });
    expect(within(screen.getByRole("banner")).queryByRole("status")).not.toBeInTheDocument();
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
          running: {
            trigger: "scheduled",
            pid: 4242,
            since: "2026-10-15T05:50:01.900",
            runs: [30],
          },
          last_run: RUNNING,
        }),
      ),
      "GET /api/runs/30": reply({ ...RUNNING, steps: STEPS, log_lines: [] }),
    });
  }

  it("shows the run as it goes in place of the next booking", async () => {
    renderLive();

    const live = await screen.findByRole("region", {
      name: "Đang đặt cho Thứ Bảy 17/10 · sân Tennis S6",
    });
    expect(within(live).getByText("15:00–16:00")).toBeInTheDocument();
    expect(within(live).getByText("LƯỢT 1/2")).toBeInTheDocument();
    const newest = within(live).getByRole("listitem", { current: "step" });
    expect(newest).toHaveTextContent("Lượt 1/2: 15:00–16:00đang chạy");
    expect(within(live).getByText("16:00–17:00 · chờ tới lượt")).toBeInTheDocument();
    expect(within(live).getByText("0/2").parentElement).toHaveTextContent("0/2 khung đã đặt xong");
    expect(
      within(live).getByText(/Sân, khung giờ và chạy thử mở lại khi lần này xong/),
    ).toBeInTheDocument();
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
          running: {
            trigger: "scheduled",
            pid: 4242,
            since: "2026-10-15T05:50:01.900",
            runs: [30],
          },
          last_run: ended,
        }),
      ),
      "GET /api/runs/30": reply({ ...ended, steps: [...STEPS, finished], log_lines: [] }),
    });

    const live = await screen.findByRole("region", {
      name: "Đang đặt cho Thứ Bảy 17/10 · sân Tennis S6",
    });
    expect(await within(live).findByText("Xong: 2/2 khung thành công")).toBeInTheDocument();
    expect(within(live).queryByRole("listitem", { current: "step" })).not.toBeInTheDocument();
  });

  it("gets ready until the run holding the lock has started", async () => {
    const before = runSummary(29, { started_at: "2026-10-14T06:00:00.000" });
    renderApp(paths.overview, {
      "GET /api/status": reply(
        overview({
          running: { trigger: "dry_run", pid: 4242, since: "2026-10-15T10:00:00.000", runs: [] },
          last_run: before,
        }),
      ),
    });

    expect(await screen.findByRole("region", { name: "Đang chuẩn bị" })).toBeInTheDocument();
  });

  it("shows each MuMu instance's run when several book side by side", async () => {
    const other = { ...RUNNING, id: 31, device: 1 };
    const otherSteps = STEPS.map((item) => ({ ...item, id: item.id + 100, run_id: 31 }));
    renderApp(paths.overview, {
      "GET /api/status": reply(
        overview({
          running: {
            trigger: "scheduled",
            pid: 4242,
            since: "2026-10-15T05:50:01.900",
            runs: [30, 31],
          },
          last_run: other,
        }),
      ),
      "GET /api/runs/30": reply({ ...RUNNING, device: 0, steps: STEPS, log_lines: [] }),
      "GET /api/runs/31": reply({ ...other, steps: otherSteps, log_lines: [] }),
    });

    const first = await screen.findByRole("region", {
      name: "MuMu 0 · Đang đặt cho Thứ Bảy 17/10 · sân Tennis S6",
    });
    const second = await screen.findByRole("region", {
      name: "MuMu 1 · Đang đặt cho Thứ Bảy 17/10 · sân Tennis S6",
    });
    expect(within(first).getByText("LƯỢT 1/2")).toBeInTheDocument();
    expect(within(second).getByText("LƯỢT 1/2")).toBeInTheDocument();
    // The note that the choices wait comes once, under the last ticket.
    expect(screen.getAllByText(/mở lại khi lần này xong/)).toHaveLength(1);
    expect(within(second).getByText(/mở lại khi lần này xong/)).toBeInTheDocument();
  });

  it("gets ready while a dry run the app started has no step yet", async () => {
    renderApp(paths.overview, {
      "GET /api/status": reply(
        overview({ running: { trigger: "dry_run", pid: 4242, since: null, runs: [] } }),
      ),
    });

    expect(await screen.findByRole("region", { name: "Đang chuẩn bị" })).toBeInTheDocument();
  });

  it("names a dry run as such", async () => {
    const dry = STEPS.map((item, index) =>
      index === 0 ? { ...item, data: { trigger: "dry_run", slots: SLOTS, dry_run: true } } : item,
    );
    renderApp(paths.overview, {
      "GET /api/status": reply(
        overview({
          running: { trigger: "dry_run", pid: 4242, since: "2026-10-15T05:50:01.900", runs: [30] },
          last_run: { ...RUNNING, dry_run: true, trigger: "dry_run" },
        }),
      ),
      "GET /api/runs/30": reply({ ...RUNNING, steps: dry, log_lines: [] }),
    });

    const live = await screen.findByRole("region", {
      name: "Đang chạy thử cho Thứ Bảy 17/10 · sân Tennis S6",
    });
    expect(within(live).getByText("0/2").parentElement).toHaveTextContent("0/2 khung đã qua");
  });

  it("keeps the next booking in view during auto setup, its dry run locked", async () => {
    renderOverview(
      overview({ running: { trigger: "setup", pid: 4242, since: "21:00:00", runs: [] } }),
    );

    expect(await screen.findByText("Đang thiết lập tự động")).toBeInTheDocument();
    const ticket = await screen.findByRole("region", { name: "Lần đặt tiếp theo" });
    expect(
      within(ticket).getByText("Chạy thử và Thiết lập tự động tạm khóa cho tới khi xong"),
    ).toBeInTheDocument();
    expect(within(ticket).getByRole("button", { name: "Chạy thử ngay" })).toBeDisabled();
  });
});

describe("HomePage panel", () => {
  it("opens on the History once everything is set up", async () => {
    renderOverview(overview());
    await statusLine();

    expect(screen.getByRole("tab", { name: "Lịch sử" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Thiết lập" })).toHaveAttribute(
      "aria-selected",
      "false",
    );
  });

  it("opens on the Setup while a task is left, with their count", async () => {
    tickSteps({ mumu: true, app: true, login: false });
    renderOverview(overview());

    expect(await screen.findByRole("tab", { name: "Thiết lập, còn 1 việc" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tabpanel", { name: "Thiết lập, còn 1 việc" })).toBeInTheDocument();
  });

  it("opens on the Setup until the daily booking is on", async () => {
    const status = overview();
    renderOverview({ ...status, schedule: { ...status.schedule, enabled: false } });

    // The panel waits on the History until the status comes in.
    await waitFor(() =>
      expect(screen.getByRole("tab", { name: "Thiết lập" })).toHaveAttribute(
        "aria-selected",
        "true",
      ),
    );
  });

  it("opens on the History when the address asks for a run", async () => {
    tickSteps({ mumu: false, app: false, login: false });
    renderApp(`${paths.overview}?run=26`, { "GET /api/status": reply(overview()) });

    expect(await screen.findByRole("tab", { name: /^Lịch sử/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("changes tabs on a press and with the arrow keys", async () => {
    renderOverview(overview());
    await statusLine();
    const history = screen.getByRole("tab", { name: "Lịch sử" });

    fireEvent.click(screen.getByRole("tab", { name: "Thiết lập" }));
    expect(screen.getByRole("tab", { name: "Thiết lập" })).toHaveAttribute("aria-selected", "true");

    fireEvent.keyDown(screen.getByRole("tab", { name: "Thiết lập" }), { key: "ArrowLeft" });
    expect(history).toHaveAttribute("aria-selected", "true");
    expect(history).toHaveFocus();
  });
});
