import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { paths } from "../../paths";
import { renderApp } from "../../test/app";
import { reply, requestsTo } from "../../test/backend";
import { step } from "../../test/liveSocket";
import { runSummary } from "../../test/runs";

/** This morning's 06:00 run: the first slot booked, the second full. */
const PARTIAL = runSummary(26, {
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

/** Last night's dry run: it went through its one slot. */
const DRY = runSummary(25, {
  trigger: "dry_run",
  dry_run: true,
  started_at: "2026-10-14T19:43:00.000",
  finished_at: "2026-10-14T19:44:10.000",
  booked: 1,
  total: 1,
  slots: [
    {
      slot: "18:00 - 19:00",
      ok: true,
      reason: null,
      finished_at: "2026-10-14T19:44:10.000",
      seconds: 7,
      commands: 50,
    },
  ],
});

/** A booking started by hand that stopped before any slot. */
const STOPPED = runSummary(24, {
  trigger: "manual",
  started_at: "2026-10-12T08:32:16.966",
  play_date: null,
  court: null,
  status: "failed",
  booked: 0,
  total: 0,
  slots: [],
  error: "Another run is in progress: dry_run run (pid 17156) since 08:32:10",
});

const RUNS = [PARTIAL, DRY, STOPPED];

/** Run 26 in full: its slots, its steps and two lines of its log. */
const RUN_26 = {
  ...PARTIAL,
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

/** The History tab of the panel beside the next booking. */
function panel() {
  return screen.findByRole("tabpanel", { name: "Lịch sử" });
}

/** The rows of the list, as their text. */
async function rows() {
  const list = await within(await panel()).findByRole("list");
  return within(list)
    .getAllByRole("link")
    .map((link) => link.textContent);
}

beforeEach(() => {
  // Today is 15/10: the rows name this morning and last night.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 15, 9, 30));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("History list", () => {
  it("lists the real bookings: what they booked, each slot and why it failed", async () => {
    const { fetch } = renderApp(paths.overview, REPLIES);

    expect(await rows()).toEqual([
      "Chơi Thứ Bảy 17/10 · S6ĐẶT ĐƯỢC 1/2đặt sáng nay 15/10 · theo hẹn giờ✓ 15:00✕ 16:00 Hết chỗ",
      "Lần chạy Thứ Hai 12/10KHÔNG ĐẶT ĐƯỢCđặt sáng Thứ Hai 12/10 · chạy tay✕ Đang có lần chạy khác",
    ]);
    const query = new URL(fetch.mock.calls.find(([r]) => r.url.includes("/api/runs"))![0].url);
    expect(Object.fromEntries(query.searchParams)).toEqual({ days: "10", limit: "500" });
  });

  it("adds the dry runs on request, without asking the backend again", async () => {
    const { fetch } = renderApp(paths.overview, REPLIES);
    await rows();

    fireEvent.click(screen.getByRole("checkbox", { name: "Gồm cả chạy thử" }));

    const shown = await rows();
    expect(shown).toHaveLength(3);
    expect(shown[1]).toBe("Chơi Thứ Bảy 17/10 · S6CHẠY THỬ ĐẠTchạy thử tối hôm qua 14/10○ 18:00");
    expect(requestsTo(fetch, "GET /api/runs")).toBe(1);
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
    const { fetch } = renderApp(paths.overview, replies);
    expect(await rows()).toHaveLength(10);
    const history = await panel();
    expect(within(history).getByText("10 ngày gần nhất")).toBeInTheDocument();

    replies["GET /api/runs"] = reply(older);
    fireEvent.click(within(history).getByRole("button", { name: "Xem thêm 10 ngày trước" }));

    await waitFor(async () => expect(await rows()).toHaveLength(12));
    expect((await rows()).at(-1)).toContain("đặt sáng Thứ Sáu 02/10");
    const query = new URL(fetch.mock.calls.at(-1)![0].url).searchParams;
    expect(Object.fromEntries(query)).toEqual({ days: "10", limit: "500", before: "111" });
    expect(within(history).queryByRole("button")).not.toBeInTheDocument();
    expect(within(history).queryByText(/ngày gần nhất/)).not.toBeInTheDocument();
  });

  it("says when there is no run yet", async () => {
    renderApp(paths.overview, { "GET /api/runs": reply([]) });

    expect(await within(await panel()).findByText("Chưa có lần chạy nào.")).toBeInTheDocument();
  });

  it("names the MuMu instance of a run that booked beside the first one", async () => {
    const other = runSummary(27, { device: 1, court: "S9 - Sân tennis", booked: 2 });
    renderApp(paths.overview, { "GET /api/runs": reply([other, { ...PARTIAL, device: 0 }]) });

    const [first, second] = await rows();
    expect(first).toContain("đặt sáng nay 15/10 · theo hẹn giờ · MuMu 1");
    expect(second).toContain("đặt sáng nay 15/10 · theo hẹn giờ✓"); // the first instance
  });

  it("says when there are dry runs only", async () => {
    renderApp(paths.overview, { "GET /api/runs": reply([DRY]) });

    const history = await panel();
    expect(await within(history).findByText("Chưa có lần đặt thật nào.")).toBeInTheDocument();
  });

  it("reads in English", async () => {
    await i18n.changeLanguage("en");
    renderApp(paths.overview, REPLIES);

    const history = await screen.findByRole("tabpanel", { name: "History" });
    const list = await within(history).findByRole("list");
    expect(within(list).getAllByRole("link")[0]).toHaveTextContent(
      "Play Sat 17 Oct · S6BOOKED 1/2booked this morning 15 Oct · on schedule✓ 15:00✕ 16:00 Fully booked",
    );
  });
});

describe("History run", () => {
  it("opens a run in place of the list, and goes back to it", async () => {
    const { router } = renderApp(paths.overview, REPLIES);
    await rows();
    fireEvent.click(screen.getByRole("checkbox", { name: "Gồm cả chạy thử" }));

    fireEvent.click(screen.getByRole("link", { name: /^Chơi Thứ Bảy 17\/10 · S6ĐẶT ĐƯỢC/ }));

    const run = await screen.findByRole("article", { name: "Chơi Thứ Bảy 17/10 · S6" });
    expect(router.state.location.search).toBe("?run=26");
    expect(within(run).getByText("ĐẶT ĐƯỢC 1/2")).toBeInTheDocument();
    expect(within(run).getByText("đặt sáng nay 15/10 · theo hẹn giờ")).toBeInTheDocument();
    const [booked, failed] = within(run).getAllByRole("list")[0]!.querySelectorAll("li");
    expect(booked).toHaveTextContent("15:00–16:00ĐÃ ĐẶTXong lúc 06:00:06 · mất 6,0 giây");
    expect(failed).toHaveTextContent("16:00–17:00KHÔNG ĐẶT ĐƯỢCHết chỗ");

    fireEvent.click(screen.getByRole("link", { name: "← Lịch sử" }));

    expect(await rows()).toHaveLength(3);
    expect(router.state.location.search).toBe("");
    expect(screen.getByRole("checkbox", { name: "Gồm cả chạy thử" })).toBeChecked();
  });

  it("shows every step of the run and the engine's reason", async () => {
    renderApp(`${paths.overview}?run=26`, REPLIES);

    const run = await screen.findByRole("article", { name: "Chơi Thứ Bảy 17/10 · S6" });
    const steps = within(run).getAllByRole("list")[1]!.querySelectorAll("li");
    expect([...steps].map((item) => item.textContent)).toEqual([
      "05:50:02Bắt đầu theo hẹn giờ",
      "06:00:00Bắt đầu đặt cho Thứ Bảy 17/10 · sân S6",
      "06:00:06✓ Đặt được 15:00–16:00 (6,0 giây)",
      "06:00:11✕ Không đặt được 16:00–17:00 (4,3 giây)Slot 16:00 - 17:00 is fully booked",
    ]);
    expect(within(run).getByText("Bắt đầu đặt cho Thứ Bảy 17/10 · sân S6").tagName).toBe("MARK");
  });

  it("keeps the technical log closed until asked for", async () => {
    renderApp(`${paths.overview}?run=26`, REPLIES);

    const summary = await screen.findByText("Chi tiết kỹ thuật");
    const details = summary.closest("details");
    expect(details).not.toHaveAttribute("open");
    // The log keeps its columns, so the text is compared as it is.
    expect(details?.textContent).toContain("05:50:02.073 INFO    court-booker 0.6.0");
  });

  it("says a dry run booked nothing", async () => {
    renderApp(`${paths.overview}?run=25`, {
      "GET /api/runs/25": reply({ ...DRY, steps: [], log_lines: [] }),
    });

    const run = await screen.findByRole("article", { name: "Chơi Thứ Bảy 17/10 · S6" });
    expect(within(run).getByText("CHẠY THỬ ĐẠT")).toBeInTheDocument();
    expect(within(run).getByText("chạy thử tối hôm qua 14/10")).toBeInTheDocument();
    expect(within(run).getAllByRole("listitem")[0]).toHaveTextContent(
      '18:00–19:00TỚI XÁC NHẬNDừng trước nút "Xác nhận", không đặt thật',
    );
  });

  it("says why a run stopped before any slot", async () => {
    renderApp(`${paths.overview}?run=24`, {
      "GET /api/runs/24": reply({ ...STOPPED, steps: [], log_lines: [] }),
    });

    const run = await screen.findByRole("article", { name: "Lần chạy Thứ Hai 12/10" });
    expect(within(run).getByText("Đang có lần chạy khác")).toBeInTheDocument();
  });

  it("adds the steps of a running run as the live feed brings them", async () => {
    const { live } = renderApp(`${paths.overview}?run=26`, REPLIES);
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
    renderApp(`${paths.overview}?run=99`, REPLIES);

    const history = await panel();
    expect(await within(history).findByRole("alert")).toHaveTextContent(
      "Không tìm thấy dữ liệu này.",
    );
  });
});
