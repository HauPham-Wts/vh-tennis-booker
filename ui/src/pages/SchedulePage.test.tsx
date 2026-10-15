import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Overview, RunSummary } from "../api/types";
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
    "GET /api/runs": reply(dryRuns),
    ...extra,
  };
  return { replies, ...renderApp(paths.schedule, replies) };
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
