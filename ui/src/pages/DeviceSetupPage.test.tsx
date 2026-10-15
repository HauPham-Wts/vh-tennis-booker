import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Overview, SetupItem } from "../api/types";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { type Reply, reply, requestsTo } from "../test/backend";
import { overview } from "../test/overview";
import { runSummary } from "../test/runs";

/** Every check as GET /api/setup gives it on a PC set up for booking. */
function checks(fields: Partial<Record<string, SetupItem["status"]>> = {}): SetupItem[] {
  const statuses = {
    mumu_installed: "ok",
    mumu_screen: "ok",
    wake_timers: "ok",
    app_installed: "ok",
    ...fields,
  } as const;
  return Object.entries(statuses).map(([item, status]) => ({ item, status, detail: "" }));
}

function renderSetup(
  status: Overview = overview(),
  items: SetupItem[] = checks(),
  auto: Reply = reply(items),
) {
  return renderApp(paths.deviceSetup, {
    "GET /api/status": reply(status),
    "GET /api/setup": reply(items),
    "POST /api/setup/auto": auto,
  });
}

/** The bodies of the auto setup requests the page sent, in order. */
async function autoBodies(fetch: ReturnType<typeof renderSetup>["fetch"]): Promise<unknown[]> {
  const posts = fetch.mock.calls
    .map(([request]) => request)
    .filter((request) => request.method === "POST");
  return Promise.all(posts.map((request) => request.clone().json() as Promise<unknown>));
}

/** The status of an auto setup row, found by its item. */
function autoRow(item: string) {
  return screen.getByRole("rowheader", { name: item }).closest("tr") as HTMLElement;
}

/** The card of a manual step, found by its title. */
async function step(title: string) {
  const heading = await screen.findByRole("heading", { level: 3, name: title });
  return heading.closest("li") as HTMLElement;
}

describe("DeviceSetupPage manual steps", () => {
  it("marks the three steps done on a PC ready to book", async () => {
    renderSetup();

    await waitFor(() => expect(screen.getAllByText("ĐÃ XONG")).toHaveLength(3));
    expect(screen.getByText("Xong 3/3")).toBeInTheDocument();
  });

  it("asks to install MuMu and frames it as the next step", async () => {
    renderSetup(overview(), checks({ mumu_installed: "user", app_installed: "unknown" }));

    const mumu = await step("Cài MuMu Player");
    await waitFor(() => expect(within(mumu).getByText("CHƯA XONG")).toBeInTheDocument());
    expect(mumu).toHaveTextContent("Tải MuMu Player ở mumuplayer.com");
    expect(mumu.className).toMatch(/current/);
    expect((await step("Cài app Vinhomes Resident trong MuMu")).className).not.toMatch(/current/);
  });

  it("asks to open MuMu when the app cannot be checked", async () => {
    renderSetup(overview(), checks({ app_installed: "unknown" }));

    const app = await step("Cài app Vinhomes Resident trong MuMu");
    await waitFor(() => expect(within(app).getByText("CHƯA RÕ")).toBeInTheDocument());
    expect(app).toHaveTextContent("Mở MuMu rồi bấm Kiểm tra lại");
    expect(screen.getByText("Xong 2/3")).toBeInTheDocument();
  });

  it("asks to log in again after a run the app did not let in", async () => {
    const error =
      "The app did not show 'Trang chủ' or 'Sân Tennis' in 60 s; check that it is logged in";
    renderSetup(overview({ last_run: runSummary(30, { status: "failed", error }) }));

    const login = await step("Đăng nhập app Vinhomes");
    expect(within(login).getByText("CHƯA XONG")).toBeInTheDocument();
    expect(login).toHaveTextContent("Lần chạy gần nhất không vào được app.");
  });

  it("sends a PC without a passed dry run to the schedule", async () => {
    const status = overview();
    renderSetup({ ...status, schedule: { ...status.schedule, dry_run_passed: false } });

    const login = await step("Đăng nhập app Vinhomes");
    expect(within(login).getByText("CHƯA RÕ")).toBeInTheDocument();
    expect(within(login).getByRole("link", { name: "Mở Hẹn giờ" })).toHaveAttribute(
      "href",
      paths.schedule,
    );
  });

  it("says the steps are being checked until the checks answer", async () => {
    renderSetup();

    const mumu = await step("Cài MuMu Player");
    expect(within(mumu).getByText("ĐANG KIỂM TRA")).toBeInTheDocument();
    await waitFor(() => expect(within(mumu).getByText("ĐÃ XONG")).toBeInTheDocument());
  });

  it("checks nothing while a run holds the lock", async () => {
    const { fetch } = renderSetup(
      overview({ running: { trigger: "scheduled", pid: 4242, since: "2026-10-16T05:50:01" } }),
    );

    expect(await screen.findByText(/Đang có một lần chạy\./)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Kiểm tra lại" })).toBeDisabled();
    expect(within(await step("Cài MuMu Player")).getByText("CHƯA RÕ")).toBeInTheDocument();
    expect(requestsTo(fetch, "GET /api/setup")).toBe(0);
  });

  it("checks again on request", async () => {
    const { fetch } = renderSetup();
    await waitFor(() => expect(screen.getAllByText("ĐÃ XONG")).toHaveLength(3));

    fireEvent.click(await screen.findByRole("button", { name: "Kiểm tra lại" }));

    await waitFor(() => expect(requestsTo(fetch, "GET /api/setup")).toBe(2));
    expect(requestsTo(fetch, "GET /api/status")).toBe(2);
  });
});

describe("DeviceSetupPage auto setup", () => {
  it("shows each item it takes care of and when it is locked", async () => {
    renderSetup(overview(), checks({ wake_timers: "fixable" }));

    await waitFor(() => expect(autoRow("Tìm nơi cài MuMu")).toHaveTextContent("✓ Đã đúng"));
    expect(autoRow("Màn hình MuMu 540 × 1600, DPI 220")).toHaveTextContent("✓ Đã đúng");
    expect(autoRow("Cho phép máy tự thức dậy")).toHaveTextContent("Cần sửa");
    expect(
      screen.getByText("Tạm khóa từ 05:50 đến 06:05 để không làm gián đoạn lần đặt sân."),
    ).toBeInTheDocument();
  });

  it("fixes what it can without restarting MuMu", async () => {
    const after = checks({ wake_timers: "fixed" });
    const { fetch } = renderSetup(overview(), checks({ wake_timers: "fixable" }), reply(after));

    fireEvent.click(await screen.findByRole("button", { name: "Thiết lập tự động" }));

    await waitFor(() => expect(autoRow("Cho phép máy tự thức dậy")).toHaveTextContent("Vừa sửa"));
    expect(await autoBodies(fetch)).toEqual([{ restart_mumu: false }]);
    expect(screen.queryByRole("button", { name: "Khởi động lại MuMu" })).not.toBeInTheDocument();
  });

  it("asks before restarting an open MuMu to set its screen", async () => {
    const before = checks({ mumu_screen: "fixable" });
    const { fetch, cache } = renderSetup(overview(), before, reply(before));
    fireEvent.click(await screen.findByRole("button", { name: "Thiết lập tự động" }));

    const restart = await screen.findByRole("button", { name: "Khởi động lại MuMu" });
    expect(screen.getByText(/Cần khởi động lại MuMu\./)).toBeInTheDocument();
    // The restart answers with the screen set.
    fetch.mockImplementationOnce(() =>
      Promise.resolve(
        new Response(JSON.stringify(checks({ mumu_screen: "fixed" })), {
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    fireEvent.click(restart);

    await waitFor(() =>
      expect(autoRow("Màn hình MuMu 540 × 1600, DPI 220")).toHaveTextContent("Vừa sửa"),
    );
    expect(await autoBodies(fetch)).toEqual([{ restart_mumu: false }, { restart_mumu: true }]);
    expect(screen.queryByRole("button", { name: "Khởi động lại MuMu" })).not.toBeInTheDocument();
    expect(cache.getQueryData(["setup"])).toEqual(checks({ mumu_screen: "fixed" }));
  });

  it("stays locked while a run holds the lock", async () => {
    renderSetup(overview({ running: { trigger: "dry_run", pid: 4242, since: null } }));

    expect(await screen.findByRole("button", { name: "Thiết lập tự động" })).toBeDisabled();
    expect(
      screen.getByText("Chạy thử và Thiết lập tự động tạm khóa cho tới khi xong"),
    ).toBeInTheDocument();
  });

  it("says why it could not start", async () => {
    const quiet = { error: "bad_request", detail: "No auto setup from 05:50 to 06:05" };
    renderSetup(overview(), checks(), reply(quiet, 400));

    fireEvent.click(await screen.findByRole("button", { name: "Thiết lập tự động" }));

    expect(await screen.findByText("Chưa làm được việc này lúc này.")).toBeInTheDocument();
  });
});
