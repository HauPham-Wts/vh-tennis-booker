import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Overview, RunSummary, ScheduleState } from "../api/types";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { type Reply, reply, requestsTo } from "../test/backend";
import { overview } from "../test/overview";
import { runSummary } from "../test/runs";

/** A dry run of 15/10 at 09:12, as GET /api/runs?dry_run=true gives it. */
function dryRun(fields: Partial<RunSummary> = {}): RunSummary {
  return runSummary(31, {
    trigger: "dry_run",
    dry_run: true,
    started_at: "2026-10-15T09:12:00.000",
    finished_at: "2026-10-15T09:13:02.000",
    ...fields,
  });
}

function renderSchedule(
  status: Overview = overview(),
  dryRuns: RunSummary[] = [],
  extra: Record<string, Reply> = {},
) {
  const replies: Record<string, Reply> = {
    "GET /api/status": reply(status),
    "GET /api/schedule": reply(status.schedule),
    "GET /api/runs": reply(dryRuns),
    ...extra,
  };
  return { replies, ...renderApp(paths.schedule, replies) };
}

/** The schedule as GET /api/schedule gives it: on, the next start tomorrow at 06:00. */
function schedule(fields: Partial<ScheduleState> = {}): ScheduleState {
  return { ...overview().schedule, ...fields };
}

/** The body of the one PUT the page sent. */
async function switchBody(fetch: ReturnType<typeof renderSchedule>["fetch"]): Promise<unknown> {
  const put = fetch.mock.calls.map(([request]) => request).find((r) => r.method === "PUT");
  expect(put).toBeDefined();
  return put?.json();
}

function dailySwitch() {
  return screen.findByRole("switch", { name: "Hẹn giờ mỗi sáng" });
}

function dryRunButton() {
  return screen.findByRole("button", { name: "Chạy thử ngay" });
}

beforeEach(() => {
  // "Today" is 15/10: the page says "sáng nay" from the clock.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 15, 10, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("SchedulePage dry run", () => {
  it("offers a first dry run, with the quiet time", async () => {
    renderSchedule();

    expect(await screen.findByText("Chưa chạy thử lần nào.")).toBeInTheDocument();
    expect(await dryRunButton()).toBeEnabled();
    expect(
      screen.getByText("Tạm khóa từ 05:50 đến 06:05 để không làm gián đoạn lần đặt sân."),
    ).toBeInTheDocument();
  });

  it("says when the last dry run passed", async () => {
    const { fetch } = renderSchedule(overview(), [dryRun()]);

    expect(
      await screen.findByText("Lần chạy thử gần nhất: sáng nay lúc 09:12 · thành công"),
    ).toBeInTheDocument();
    const runs = fetch.mock.calls.map(([request]) => new URL(request.url));
    expect(runs.find(({ pathname }) => pathname === "/api/runs")?.search).toBe(
      "?dry_run=true&limit=1",
    );
  });

  it("says why the last dry run did not pass", async () => {
    const full = { ok: false, reason: "Slot 15:00 - 16:00 is fully booked" };
    const slots = dryRun().slots.map((slot, index) => (index === 0 ? { ...slot, ...full } : slot));
    renderSchedule(overview(), [dryRun({ status: "partial", booked: 1, slots })]);

    expect(
      await screen.findByText("Lần chạy thử gần nhất: sáng nay lúc 09:12 · không qua: Hết chỗ"),
    ).toBeInTheDocument();
  });

  it("starts a dry run and points to its steps on the Overview", async () => {
    const started = reply({ pid: 4242, started_at: "2026-10-15T10:00:00.000" }, 202);
    const { fetch, replies } = renderSchedule(overview(), [], {
      "POST /api/runs/dry-run": started,
    });
    const button = await dryRunButton();
    replies["GET /api/status"] = reply(
      overview({ running: { trigger: "dry_run", pid: 4242, since: null } }),
    );

    fireEvent.click(button);

    expect(await screen.findByText("Đang chạy thử.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Xem từng bước ở Tổng quan →" })).toHaveAttribute(
      "href",
      paths.overview,
    );
    expect(screen.getByRole("button", { name: "Chạy thử ngay" })).toBeDisabled();
    expect(requestsTo(fetch, "POST /api/runs/dry-run")).toBe(1);
  });

  it("stays locked while the 06:00 run goes on", async () => {
    renderSchedule(
      overview({ running: { trigger: "scheduled", pid: 4242, since: "2026-10-16T05:50:01" } }),
    );

    expect(await dryRunButton()).toBeDisabled();
    expect(
      screen.getByText(/Chạy thử và Thiết lập tự động tạm khóa cho tới khi xong/),
    ).toBeInTheDocument();
  });

  it("says why a dry run could not start", async () => {
    const held = reply({ error: "lock_held", detail: "Another run is in progress" }, 409);
    renderSchedule(overview(), [], { "POST /api/runs/dry-run": held });

    fireEvent.click(await dryRunButton());

    await waitFor(() =>
      expect(
        screen.getByText("Đang có một lần chạy khác. Hãy chờ nó xong rồi thử lại."),
      ).toBeInTheDocument(),
    );
  });
});

// Only stand-in backends here: a real PUT /api/schedule rewrites the Windows task.
describe("SchedulePage daily schedule", () => {
  it("shows the times and the next booking while on", async () => {
    renderSchedule();

    expect(await dailySwitch()).toHaveAttribute("aria-checked", "true");
    expect(
      await screen.findByText(/Lần tới: sáng Thứ Sáu 16\/10 lúc 06:00, chơi Chủ Nhật 18\/10\./),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Đổi khung giờ hoặc sân" })).toHaveAttribute(
      "href",
      paths.bookingSettings,
    );
    const facts = screen.getByText("Đánh thức máy").closest("dl") as HTMLElement;
    expect(facts).toHaveTextContent("Đánh thức máy05:50Bắt đầu đặt06:00Lặp lạiMỗi ngày");
  });

  it("cannot be turned on before a dry run passed", async () => {
    const off = schedule({ enabled: false, dry_run_passed: false });
    renderSchedule(overview({ schedule: off }));

    expect(await dailySwitch()).toBeDisabled();
    expect(screen.getByText("Đang tắt: máy sẽ không tự đặt sân.", { exact: false })).toBeVisible();
    expect(
      screen.getByText("Cần chạy thử thành công một lần trước khi bật hẹn giờ."),
    ).toBeInTheDocument();
  });

  it("turns the schedule off", async () => {
    const { fetch } = renderSchedule(overview(), [], {
      "PUT /api/schedule": reply(schedule({ enabled: false })),
    });

    fireEvent.click(await dailySwitch());

    await waitFor(async () => expect(await dailySwitch()).toHaveAttribute("aria-checked", "false"));
    expect(await switchBody(fetch)).toEqual({ enabled: false });
  });

  it("turns the schedule on once a dry run passed", async () => {
    const off = schedule({ enabled: false });
    const { fetch } = renderSchedule(overview({ schedule: off }), [], {
      "PUT /api/schedule": reply(schedule()),
    });

    fireEvent.click(await dailySwitch());

    await waitFor(async () => expect(await dailySwitch()).toHaveAttribute("aria-checked", "true"));
    expect(await switchBody(fetch)).toEqual({ enabled: true });
  });

  it("says why the switch failed", async () => {
    const failed = reply({ error: "schedule", detail: "schtasks failed" }, 500);
    renderSchedule(overview(), [], { "PUT /api/schedule": failed });

    fireEvent.click(await dailySwitch());

    expect(
      await screen.findByText("Không đọc hoặc đổi được lịch hẹn giờ của Windows."),
    ).toBeInTheDocument();
  });

  it("lists the habits the PC needs", async () => {
    renderSchedule();

    const habits = await screen.findByRole("heading", { name: "Để hẹn giờ chạy được khi bạn ngủ" });
    expect(habits.nextElementSibling).toHaveTextContent(
      "Cho máy Sleep, đừng Shut downKhông đăng xuất khỏi WindowsLaptop thì cắm sạc",
    );
  });
});
