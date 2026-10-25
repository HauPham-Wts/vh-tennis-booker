import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Overview, RunSummary, ScheduleState, Settings } from "../../api/types";
import { paths } from "../../paths";
import { renderApp } from "../../test/app";
import { type Reply, reply, requestsTo } from "../../test/backend";
import { overview } from "../../test/overview";
import { runSummary } from "../../test/runs";
import { settings } from "../../test/settings";

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

interface Backend {
  status?: Overview;
  saved?: Settings;
  runs?: RunSummary[];
  extra?: Record<string, Reply>;
}

// Only stand-in backends here: a real PUT /api/schedule rewrites the Windows task.
function renderTicket({
  status = overview(),
  saved = settings(),
  runs = [],
  extra = {},
}: Backend = {}) {
  const replies: Record<string, Reply> = {
    "GET /api/status": reply(status),
    "GET /api/settings": reply(saved),
    "PUT /api/settings": reply(saved),
    "GET /api/runs": reply(runs),
    ...extra,
  };
  return { replies, ...renderApp(paths.overview, replies) };
}

/** The schedule with some fields changed. */
function schedule(fields: Partial<ScheduleState>): Overview {
  const status = overview();
  return { ...status, schedule: { ...status.schedule, ...fields } };
}

/** The values on top of the ticket: play day, court, slots. */
function shown(top: HTMLElement): (string | null)[] {
  return within(top)
    .getAllByRole("definition")
    .map((value) => value.textContent);
}

function ticket() {
  return screen.findByRole("region", { name: "Lần đặt tiếp theo" });
}

/** The bodies of the requests sent with `method` to `path`. */
async function bodies(
  fetch: ReturnType<typeof renderTicket>["fetch"],
  key: string,
): Promise<unknown[]> {
  const sent = fetch.mock.calls
    .map(([request]) => request)
    .filter((request) => `${request.method} ${new URL(request.url).pathname}` === key);
  return Promise.all(sent.map((request) => request.clone().json() as Promise<unknown>));
}

beforeEach(() => {
  // "Today" is 15/10: the next start, 16/10 at 06:00, is "sáng mai".
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 15, 10, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("BookingTicket start", () => {
  it("shows what is set: the play day, court and slots, and when it starts", async () => {
    renderTicket();

    const top = await ticket();
    // The badge before each slot gives its booking order.
    await waitFor(() => expect(shown(top)).toEqual(["CN 18/10", "S6", "115:00–16:00216:00–17:00"]));
    expect(within(top).getByText("Đặt lúc 06:00 sáng mai · máy thức 05:50")).toBeInTheDocument();
    const toggle = within(top).getByRole("switch", { name: "Tự đặt mỗi sáng" });
    expect(toggle).toHaveAttribute("aria-checked", "true");
    expect(toggle).toHaveTextContent("BẬT");
    expect(toggle).toBeEnabled();
  });

  it("keeps the switch locked until a dry run has passed", async () => {
    renderTicket({ status: schedule({ enabled: false, dry_run_passed: false }) });

    const top = await ticket();
    expect(within(top).getByRole("switch", { name: "Tự đặt mỗi sáng" })).toBeDisabled();
    expect(within(top).getByText("Chưa bật")).toBeInTheDocument();
    expect(
      within(top).getByText("Chạy thử thành công một lần thì mới bật được."),
    ).toBeInTheDocument();
  });

  it("does not turn itself on after a dry run passed, but asks for it", async () => {
    const { fetch, replies } = renderTicket({ status: schedule({ enabled: false }) });
    const top = await ticket();
    const toggle = within(top).getByRole("switch", { name: "Tự đặt mỗi sáng" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(toggle.parentElement?.className).toMatch(/remind/);
    expect(within(top).getByText("Máy sẽ không tự đặt sân sáng mai.")).toBeInTheDocument();
    replies["PUT /api/schedule"] = reply(overview().schedule);

    fireEvent.click(toggle);

    await waitFor(async () =>
      expect(await bodies(fetch, "PUT /api/schedule")).toEqual([{ enabled: true }]),
    );
  });
});

describe("BookingTicket choices", () => {
  it("offers no play day: it is always two days after the start", async () => {
    renderTicket();

    await screen.findByRole("group", { name: "Sân" });
    expect(screen.queryByRole("button", { name: /18\/10/ })).not.toBeInTheDocument();
  });

  it("shows the court and the slots in booking order, the rest blocked at two", async () => {
    renderTicket({ saved: settings({ slots: ["16:00 - 17:00", "15:00 - 16:00"] }) });

    const courts = await screen.findByRole("group", { name: "Sân" });
    expect(within(courts).getByRole("button", { name: "S6" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    const slots = screen.getByRole("group", { name: /^Khung giờ/ });
    expect(within(slots).getByRole("button", { name: "16:00–17:00, lượt 1" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(within(slots).getByRole("button", { name: "15:00–16:00, lượt 2" })).toBeInTheDocument();
    expect(within(slots).getByRole("button", { name: "18:00–19:00" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(within(slots).getAllByRole("button")).toHaveLength(13);
    expect(within(slots).getByText("Bấm là lưu")).toBeInTheDocument();
  });

  it("saves a press at once, keeping the developer's settings", async () => {
    const saved = settings();
    const { fetch, replies } = renderTicket({ saved });
    const courts = await screen.findByRole("group", { name: "Sân" });
    replies["PUT /api/settings"] = reply({ ...saved, court: "S9 - Sân tennis" });

    fireEvent.click(within(courts).getByRole("button", { name: "S9" }));

    await waitFor(() =>
      expect(within(courts).getByRole("button", { name: "S9" })).toHaveAttribute(
        "aria-pressed",
        "true",
      ),
    );
    expect(await bodies(fetch, "PUT /api/settings")).toEqual([
      { ...saved, court: "S9 - Sân tennis" },
    ]);
    expect(await screen.findByText("✓ Đã lưu")).toBeInTheDocument();
  });

  it("offers no instance choice for one MuMu instance", async () => {
    renderTicket();

    await screen.findByRole("group", { name: "Sân" });
    expect(screen.queryByRole("group", { name: "Máy" })).not.toBeInTheDocument();
  });

  it("shows and saves the choices of each MuMu instance", async () => {
    const other = {
      mumu_index: 1,
      slots: ["20:00 - 21:00"],
      court: "S9 - Sân tennis",
      venue_keyword: "Origami",
    };
    const saved = settings({ instances: [other] });
    const { fetch, replies } = renderTicket({ saved });
    const instances = await screen.findByRole("group", { name: "Máy" });
    const courts = screen.getByRole("group", { name: "Sân" });
    expect(within(instances).getByRole("button", { name: "MuMu 0" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(within(courts).getByRole("button", { name: "S6" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    fireEvent.click(within(instances).getByRole("button", { name: "MuMu 1" }));

    expect(within(courts).getByRole("button", { name: "S9" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    const slots = screen.getByRole("group", { name: /^Khung giờ/ });
    expect(within(slots).getByRole("button", { name: "20:00–21:00, lượt 1" })).toBeInTheDocument();
    expect(shown(await ticket())).toEqual(["CN 18/10", "S9", "120:00–21:00"]);
    const moved = { ...other, court: "S10 - Sân tennis" };
    replies["PUT /api/settings"] = reply({ ...saved, instances: [moved] });

    fireEvent.click(within(courts).getByRole("button", { name: "S10" }));

    await waitFor(() =>
      expect(within(courts).getByRole("button", { name: "S10" })).toHaveAttribute(
        "aria-pressed",
        "true",
      ),
    );
    // The first instance keeps its own court.
    expect(await bodies(fetch, "PUT /api/settings")).toEqual([{ ...saved, instances: [moved] }]);
  });

  it("takes no press while a save is on its way", async () => {
    let answer: (response: Response) => void = () => undefined;
    const { fetch } = renderTicket();
    const courts = await screen.findByRole("group", { name: "Sân" });
    const stub = fetch.getMockImplementation();
    fetch.mockImplementation((request) =>
      request.method === "PUT"
        ? new Promise<Response>((resolve) => {
            answer = resolve;
          })
        : stub!(request),
    );

    fireEvent.click(within(courts).getByRole("button", { name: "S8" }));
    expect(await screen.findByText("Đang lưu…")).toBeInTheDocument();
    expect(shown(await ticket())[1]).toBe("S8"); // the top follows the press at once
    expect(within(courts).getByRole("button", { name: "S8" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    fireEvent.click(within(courts).getByRole("button", { name: "S9" }));

    expect(requestsTo(fetch, "PUT /api/settings")).toBe(1);
    await act(async () => {
      answer(Response.json(settings({ court: "S8 - Sân tennis" })));
      await Promise.resolve();
    });
    expect(await screen.findByText("✓ Đã lưu")).toBeInTheDocument();
  });

  it("adds a slot after the ones chosen", async () => {
    const saved = settings({ slots: ["18:00 - 19:00"] });
    const { fetch } = renderTicket({ saved });
    const slots = await screen.findByRole("group", { name: /^Khung giờ/ });

    fireEvent.click(within(slots).getByRole("button", { name: "07:00–08:00" }));

    await waitFor(async () =>
      expect(await bodies(fetch, "PUT /api/settings")).toEqual([
        { ...saved, slots: ["18:00 - 19:00", "07:00 - 08:00"] },
      ]),
    );
  });

  it("says why a third slot is not added, and saves nothing", async () => {
    const { fetch } = renderTicket();
    const slots = await screen.findByRole("group", { name: /^Khung giờ/ });

    fireEvent.click(within(slots).getByRole("button", { name: "18:00–19:00" }));

    expect(within(slots).getByText("Đã đủ 2 khung: bỏ một khung trước")).toBeInTheDocument();
    expect(requestsTo(fetch, "PUT /api/settings")).toBe(0);
  });

  it("keeps the last slot", async () => {
    const { fetch } = renderTicket({ saved: settings({ slots: ["18:00 - 19:00"] }) });
    const slots = await screen.findByRole("group", { name: /^Khung giờ/ });

    fireEvent.click(within(slots).getByRole("button", { name: "18:00–19:00, lượt 1" }));

    expect(within(slots).getByText("Cần ít nhất một khung giờ")).toBeInTheDocument();
    expect(requestsTo(fetch, "PUT /api/settings")).toBe(0);
  });

  it("shows more than two slots set by hand, and takes one off", async () => {
    const saved = settings({ slots: ["15:00 - 16:00", "16:00 - 17:00", "18:00 - 19:00"] });
    const { fetch } = renderTicket({ saved });
    const slots = await screen.findByRole("group", { name: /^Khung giờ/ });
    expect(within(slots).getByRole("button", { name: "18:00–19:00, lượt 3" })).toBeInTheDocument();

    fireEvent.click(within(slots).getByRole("button", { name: "15:00–16:00, lượt 1" }));

    await waitFor(async () =>
      expect(await bodies(fetch, "PUT /api/settings")).toEqual([
        { ...saved, slots: ["16:00 - 17:00", "18:00 - 19:00"] },
      ]),
    );
  });

  it("says why a save failed and shows the saved choice again", async () => {
    const invalid = reply({ error: "invalid_settings", detail: "court: unknown" }, 422);
    renderTicket({ extra: { "PUT /api/settings": invalid } });
    const courts = await screen.findByRole("group", { name: "Sân" });

    fireEvent.click(within(courts).getByRole("button", { name: "S10" }));

    expect(await screen.findByText("Một số cài đặt chưa hợp lệ.")).toBeInTheDocument();
    expect(within(courts).getByRole("button", { name: "S6" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});

describe("BookingTicket dry run", () => {
  it("offers a first dry run, with the quiet time", async () => {
    renderTicket();

    const top = await ticket();
    expect(
      await within(top).findByText("Chưa chạy thử lần nào. Mất khoảng một phút, không đặt thật."),
    ).toBeInTheDocument();
    expect(
      within(top).getByText(
        "Không chạy thử từ 05:50 đến 06:05, để không làm gián đoạn lần đặt sân.",
      ),
    ).toBeInTheDocument();
    expect(within(top).getByRole("button", { name: "Chạy thử ngay" })).toBeEnabled();
  });

  it("says when the last dry run passed", async () => {
    const { fetch } = renderTicket({ runs: [dryRun()] });

    const line = await screen.findByText(/^Chạy thử gần nhất: sáng nay lúc 09:12/);
    expect(line).toHaveTextContent("Chạy thử gần nhất: sáng nay lúc 09:12 · thành công");
    const asked = fetch.mock.calls.map(([request]) => new URL(request.url).search);
    expect(asked).toContain("?dry_run=true&limit=1");
  });

  it("says why the last dry run did not pass", async () => {
    const full = { ok: false, reason: "Slot 15:00 - 16:00 is fully booked" };
    const slots = dryRun().slots.map((slot, index) => (index === 0 ? { ...slot, ...full } : slot));
    renderTicket({ runs: [dryRun({ status: "partial", booked: 1, slots })] });

    expect(await screen.findByText(/^Chạy thử gần nhất/)).toHaveTextContent(
      "Chạy thử gần nhất: sáng nay lúc 09:12 · không qua: Hết chỗ",
    );
  });

  it("starts a dry run", async () => {
    const started = reply({ pid: 4242, started_at: "2026-10-15T10:00:00.000" }, 202);
    const { fetch } = renderTicket({ extra: { "POST /api/runs/dry-run": started } });
    const top = await ticket();

    fireEvent.click(within(top).getByRole("button", { name: "Chạy thử ngay" }));

    await waitFor(() => expect(requestsTo(fetch, "POST /api/runs/dry-run")).toBe(1));
  });

  it("says why a dry run could not start", async () => {
    const held = reply({ error: "lock_held", detail: "Another run is in progress" }, 409);
    renderTicket({ extra: { "POST /api/runs/dry-run": held } });
    const top = await ticket();

    fireEvent.click(within(top).getByRole("button", { name: "Chạy thử ngay" }));

    expect(
      await within(top).findByText("Đang có một lần chạy khác. Hãy chờ nó xong rồi thử lại."),
    ).toBeInTheDocument();
  });
});
