import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply } from "../test/backend";
import { step } from "../test/liveSocket";
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

/** Run 26 in full: a booked slot, a failed one, and two lines of its log. */
const RUN_26 = {
  ...RUNS[0],
  status: "partial",
  booked: 1,
  slots: [],
  steps: [
    step(1, {
      run_id: 26,
      time: "2026-10-15T05:50:02.200",
      kind: "run_started",
      data: { trigger: "scheduled" },
    }),
    step(2, {
      run_id: 26,
      time: "2026-10-15T06:00:00.004",
      kind: "booking_started",
      data: { date: "2026-10-17", court: "S6 - Sân tennis" },
    }),
    step(3, {
      run_id: 26,
      time: "2026-10-15T06:00:06.120",
      kind: "slot_booked",
      category: "slot",
      data: { slot: "15:00 - 16:00", seconds: 6, dry_run: false },
    }),
    step(4, {
      run_id: 26,
      time: "2026-10-15T06:00:11.300",
      kind: "slot_failed",
      category: "error",
      data: { slot: "16:00 - 17:00", reason: "Slot 16:00 - 17:00 is fully booked", seconds: 4.3 },
    }),
  ],
  log_lines: [
    { id: 1, time: "2026-10-15T05:50:02.073", level: "INFO", message: "court-booker 0.6.0" },
    { id: 2, time: "2026-10-15T06:00:06.120", level: "INFO", message: "Booking confirmed" },
  ],
};

const REPLIES = { "GET /api/runs": reply(RUNS), "GET /api/runs/26": reply(RUN_26) };

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
    const query = new URL(fetch.mock.calls[0]![0].url).searchParams;
    expect(Object.fromEntries(query)).toEqual({ days: "10", limit: "500" });
    expect(screen.queryByRole("button", { name: "Xem thêm" })).not.toBeInTheDocument();
  });

  it("reads the ten days before the oldest run shown on request", async () => {
    // Ten days of runs, 6-15/10, then two older days.
    const newest = Array.from({ length: 10 }, (_, index) =>
      runSummary(120 - index, {
        started_at: `2026-10-${String(15 - index).padStart(2, "0")}T05:50:02.120`,
      }),
    );
    const older = [
      runSummary(105, { started_at: "2026-10-04T05:50:02.120" }),
      runSummary(104, { started_at: "2026-10-02T05:50:02.120" }),
    ];
    const replies = { "GET /api/runs": reply(newest) };
    const { fetch } = renderApp(paths.activity, replies);
    const list = await screen.findByRole("navigation", { name: "Các lần chạy" });
    expect(within(list).getAllByRole("link")).toHaveLength(10);

    replies["GET /api/runs"] = reply(older);
    fireEvent.click(within(list).getByRole("button", { name: "Xem thêm" }));

    await waitFor(() => expect(within(list).getAllByRole("link")).toHaveLength(12));
    expect(within(list).getAllByRole("link").at(-1)).toHaveTextContent("02/10 05:50");
    const query = new URL(fetch.mock.calls.at(-1)![0].url).searchParams;
    expect(Object.fromEntries(query)).toEqual({ days: "10", limit: "500", before: "111" });
    expect(within(list).queryByRole("button")).not.toBeInTheDocument();
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

  it("shows the run's result, every step and the engine's reason", async () => {
    renderApp(paths.activity, REPLIES);

    const run = await screen.findByRole("article", { name: "sáng Thứ Năm 15/10" });
    expect(within(run).getByText("hẹn giờ · chơi Thứ Bảy 17/10 · sân S6")).toBeInTheDocument();
    expect(within(run).getByText("ĐẶT ĐƯỢC 1/2")).toBeInTheDocument();
    const steps = within(run)
      .getAllByRole("listitem")
      .map((item) => item.textContent);
    expect(steps).toEqual([
      "05:50:02Bắt đầu theo hẹn giờ",
      "06:00:00Bắt đầu đặt cho Thứ Bảy 17/10 · sân S6",
      "06:00:06✓ Đặt được 15:00–16:00 (6,0 giây)",
      "06:00:11✕ Không đặt được 16:00–17:00 (4,3 giây)Slot 16:00 - 17:00 is fully booked",
    ]);
    expect(within(run).getByText("Bắt đầu đặt cho Thứ Bảy 17/10 · sân S6").tagName).toBe("MARK");
  });

  it("keeps the technical log closed until asked for", async () => {
    renderApp(paths.activity, REPLIES);

    const summary = await screen.findByText("Chi tiết kỹ thuật");
    const details = summary.closest("details");
    expect(details).not.toHaveAttribute("open");
    // The log keeps its columns, so the text is compared as it is.
    expect(details?.textContent).toContain("05:50:02.073 INFO    court-booker 0.6.0");
  });

  it("adds the steps of a running run as the live feed brings them", async () => {
    const { live } = renderApp(paths.activity, REPLIES);
    await screen.findByText("Bắt đầu theo hẹn giờ");

    act(() => {
      live.current().open();
      live.current().send(
        step(5, {
          run_id: 26,
          time: "2026-10-15T06:00:12.000",
          kind: "run_finished",
          data: { status: "partial", booked: 1, total: 2 },
        }),
      );
    });

    expect(await screen.findByText("Xong: 1/2 khung thành công")).toBeInTheDocument();
  });

  it("says when the run asked for does not exist", async () => {
    renderApp(`${paths.activity}?run=99`, { "GET /api/runs": reply(RUNS) });

    expect(await screen.findByRole("alert")).toHaveTextContent("Không tìm thấy dữ liệu này.");
  });
});
