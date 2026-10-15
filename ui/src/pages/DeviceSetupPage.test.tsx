import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Overview, SetupItem } from "../api/types";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply, requestsTo } from "../test/backend";
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

function renderSetup(status: Overview = overview(), items: SetupItem[] = checks()) {
  return renderApp(paths.deviceSetup, {
    "GET /api/status": reply(status),
    "GET /api/setup": reply(items),
  });
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
