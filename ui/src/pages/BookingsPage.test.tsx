import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply } from "../test/backend";
import { runSummary } from "../test/runs";

const MONTHS = [
  { month: "2026-10", runs: 2, booked: 3 },
  { month: "2026-09", runs: 1, booked: 2 },
];

const RUNS = [
  runSummary(26),
  runSummary(20, {
    trigger: "manual",
    started_at: "2026-10-12T09:40:00.000",
    finished_at: null,
    play_date: null,
    court: null,
    status: "running",
    booked: 0,
    total: 0,
    slots: [],
  }),
];

const REPLIES = { "GET /api/runs/months": reply(MONTHS), "GET /api/runs": reply(RUNS) };

/** Return the query of the last request for runs. */
function runsQuery(fetch: ReturnType<typeof renderApp>["fetch"]) {
  const requests = fetch.mock.calls.map(([request]) => new URL(request.url));
  return requests.filter(({ pathname }) => pathname === "/api/runs").at(-1)?.searchParams;
}

/** Return the tickets of the month, once shown (the header has list items too). */
async function bookingRows() {
  const main = screen.getByRole("main");
  await within(main).findByText("Chơi Thứ Bảy 17/10");
  return within(main).getAllByRole("listitem");
}

describe("BookingsPage", () => {
  it("sums up the newest month and lists its real bookings as tickets", async () => {
    const { fetch } = renderApp(paths.bookings, REPLIES);

    expect(
      await screen.findByText("Tháng 10/2026: đặt được 3 khung giờ trong 2 lần."),
    ).toBeInTheDocument();
    const rows = await bookingRows();
    expect(rows[0]).toHaveTextContent("Chơi Thứ Bảy 17/10");
    expect(rows[0]).toHaveTextContent("15:00–16:00 · 16:00–17:00 · sân S6");
    expect(rows[0]).toHaveTextContent("Đặt sáng 15/10 · xong lúc 06:00:11 · nhật ký");
    expect(rows[0]).toHaveTextContent("ĐẶT ĐƯỢC 2/2");
    expect(within(rows[0]!).getByRole("link", { name: "nhật ký" })).toHaveAttribute(
      "href",
      "/history/activity?run=26",
    );
    const query = runsQuery(fetch);
    expect(query?.get("month")).toBe("2026-10");
    expect(query?.get("dry_run")).toBe("false");
    expect(query?.get("limit")).toBe("200");
  });

  it("shows a run without a play date or slots in plain words", async () => {
    renderApp(paths.bookings, REPLIES);

    const rows = await bookingRows();
    expect(rows[1]).toHaveTextContent("Lần chạy Thứ Hai 12/10");
    expect(rows[1]).toHaveTextContent("Chưa thử khung giờ nào");
    expect(rows[1]).toHaveTextContent("Đặt sáng 12/10 · nhật ký");
    expect(rows[1]).toHaveTextContent("ĐANG CHẠY");
  });

  it("keeps the month picked in the address and reads that month", async () => {
    const { fetch, router } = renderApp(paths.bookings, REPLIES);

    fireEvent.change(await screen.findByRole("combobox", { name: "Tháng" }), {
      target: { value: "2026-09" },
    });

    await waitFor(() => expect(runsQuery(fetch)?.get("month")).toBe("2026-09"));
    expect(router.state.location.search).toBe("?month=2026-09");
    expect(screen.getByText("Tháng 9/2026: đặt được 2 khung giờ trong 1 lần.")).toBeInTheDocument();
  });

  it("opens the month in the address", async () => {
    renderApp(`${paths.bookings}?month=2026-09`, REPLIES);

    expect(await screen.findByRole("combobox", { name: "Tháng" })).toHaveValue("2026-09");
  });

  it("shows the newest ten days of play, then ten more on request", async () => {
    // Twelve days of play, 1-12/10, the newest one booked twice.
    const days = Array.from({ length: 12 }, (_, index) => 12 - index);
    const runs = [
      runSummary(113, { play_date: "2026-10-12" }),
      ...days.map((day, index) =>
        runSummary(112 - index, { play_date: `2026-10-${String(day).padStart(2, "0")}` }),
      ),
    ];
    const { fetch, router } = renderApp(paths.bookings, {
      "GET /api/runs/months": reply(MONTHS),
      "GET /api/runs": reply(runs),
    });
    const main = screen.getByRole("main");
    const tickets = () =>
      within(main)
        .getAllByText(/^Chơi /)
        .map((title) => title.textContent);
    const reads = () => fetch.mock.calls.filter(([request]) => request.url.endsWith("limit=200"));

    await within(main).findAllByText("Chơi Thứ Hai 12/10");
    expect(tickets()).toHaveLength(11);
    expect(tickets().at(-1)).toBe("Chơi Thứ Bảy 03/10");

    fireEvent.click(screen.getByRole("button", { name: "Xem thêm" }));

    expect(tickets()).toHaveLength(13);
    expect(tickets().at(-1)).toBe("Chơi Thứ Năm 01/10");
    expect(screen.queryByRole("button", { name: "Xem thêm" })).not.toBeInTheDocument();
    expect(reads()).toHaveLength(1);

    // Another month starts again from its newest days.
    fireEvent.change(screen.getByRole("combobox", { name: "Tháng" }), {
      target: { value: "2026-09" },
    });
    await waitFor(() => expect(router.state.location.search).toBe("?month=2026-09"));
    expect(await screen.findByRole("button", { name: "Xem thêm" })).toBeInTheDocument();
    expect(tickets()).toHaveLength(11);
  });

  it("says when there is no real booking yet, or none in the month", async () => {
    renderApp(paths.bookings, { "GET /api/runs/months": reply([]) });
    expect(await screen.findByText("Chưa có lần đặt thật nào.")).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("says when the month has no booking left to show", async () => {
    renderApp(paths.bookings, {
      "GET /api/runs/months": reply(MONTHS),
      "GET /api/runs": reply([]),
    });

    expect(await screen.findByText("Không có lần đặt nào trong tháng này.")).toBeInTheDocument();
  });
});
