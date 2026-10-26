import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Overview } from "../../api/types";
import { STORAGE_KEY } from "../../manualSteps";
import { paths } from "../../paths";
import { renderApp } from "../../test/app";
import { type Reply, reply, requestsTo } from "../../test/backend";
import { overview } from "../../test/overview";
import { settings } from "../../test/settings";

const ALL = { mumu: true, app: true, login: true };

/** Render the home screen on its Setup tab: a step is left, so it opens there. */
function renderSetup(status: Overview = overview(), extra: Record<string, Reply> = {}) {
  const replies: Record<string, Reply> = {
    "GET /api/status": reply(status),
    "GET /api/settings": reply(settings()),
    "GET /api/runs": reply([]),
    "GET /api/notifications": reply({ enabled: true, language: "vi" }),
    ...extra,
  };
  return { replies, ...renderApp(paths.overview, replies) };
}

/** The Setup tab, whatever its count. */
function setupTab() {
  return screen.findByRole("tabpanel", { name: /^Thiết lập/ });
}

/** The bodies of the requests sent as `key` ("PUT /api/notifications"). */
async function bodies(
  fetch: ReturnType<typeof renderSetup>["fetch"],
  key: string,
): Promise<unknown[]> {
  const sent = fetch.mock.calls
    .map(([request]) => request)
    .filter((request) => `${request.method} ${new URL(request.url).pathname}` === key);
  return Promise.all(sent.map((request) => request.clone().json() as Promise<unknown>));
}

beforeEach(() => {
  // "Today" is 15/10; auto setup last ran on 14/10 at 21:00.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 15, 10, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("SetupTab first use", () => {
  it("starts with how to use it, while anything is left", async () => {
    renderSetup();

    const tab = await setupTab();
    const start = within(tab).getByRole("region", {
      name: "Court Booker đặt sân thay bạn lúc 06:00 mỗi sáng, kể cả khi bạn ngủ",
    });
    expect(
      within(start)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual([
      "Làm các việc thiết lập bên dưới, một lần.",
      "Chọn môn, sân và khung giờ trên vé bên trái.",
      'Bấm "Chạy thử ngay", đạt thì bật "Tự đặt mỗi sáng".',
    ]);
  });

  it("keeps how to use it in the guide once everything is set up", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ALL));
    renderSetup();
    // Everything is set up: the panel opens on the History once the status is in.
    await within(screen.getByRole("banner")).findByText(/Sẵn sàng/);
    fireEvent.click(screen.getByRole("tab", { name: "Thiết lập" }));

    const tab = await setupTab();
    expect(within(tab).queryByRole("region", { name: /Court Booker đặt sân thay bạn/ })).toBeNull();
    expect(within(tab).getByText("Cách dùng trong 3 bước")).toBeInTheDocument();
  });
});

describe("SetupTab steps the user does", () => {
  it("ticks a step, keeps it in the browser and counts down the tasks", async () => {
    renderSetup();
    const tab = await setupTab();
    expect(screen.getByRole("tab", { name: "Thiết lập, còn 3 việc" })).toBeInTheDocument();

    fireEvent.click(within(tab).getByRole("checkbox", { name: /Đã cài MuMu Player/ }));

    expect(within(tab).getByRole("checkbox", { name: /Đã cài MuMu Player/ })).toBeChecked();
    expect(screen.getByRole("tab", { name: "Thiết lập, còn 2 việc" })).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "")).toEqual({
      mumu: true,
      app: false,
      login: false,
    });
    expect(
      within(screen.getByRole("banner")).getByText(/Còn 2 việc thiết lập/),
    ).toBeInTheDocument();
  });

  it("checks nothing with the backend", async () => {
    const { fetch } = renderSetup();
    const tab = await setupTab();

    fireEvent.click(within(tab).getByRole("checkbox", { name: /Đã đăng nhập app Vinhomes/ }));

    expect(requestsTo(fetch, "GET /api/setup")).toBe(0);
    expect(fetch.mock.calls.every(([request]) => request.method === "GET")).toBe(true);
  });
});

describe("SetupTab auto setup", () => {
  it("says all is right since its last run", async () => {
    renderSetup();

    const tab = await setupTab();
    expect(within(tab).getByText("✓ Cả 3 đã đúng · kiểm tra 14/10 lúc 21:00")).toBeInTheDocument();
  });

  it("says when it never ran", async () => {
    renderSetup(overview({ setup: null }));

    expect(within(await setupTab()).getByText("Chưa chạy lần nào")).toBeInTheDocument();
  });

  it("names what it left to fix, not what the user ticks", async () => {
    renderSetup(
      overview({
        setup: {
          checked_at: "2026-10-14T21:00:00.000",
          left: ["app_installed", "wake_timers", "mumu_screen"],
        },
      }),
    );

    expect(
      within(await setupTab()).getByText("Cần sửa: màn hình MuMu, máy tự thức dậy"),
    ).toBeInTheDocument();
  });

  it("runs, then asks before restarting MuMu for its screen", async () => {
    const checks = [
      { item: "mumu_installed", status: "ok", detail: "" },
      { item: "mumu_screen", status: "fixable", detail: "MuMu is running" },
      { item: "wake_timers", status: "ok", detail: "" },
    ];
    const { fetch } = renderSetup(overview(), { "POST /api/setup/auto": reply(checks) });
    const tab = await setupTab();

    fireEvent.click(within(tab).getByRole("button", { name: "Thiết lập tự động" }));
    fireEvent.click(await within(tab).findByRole("button", { name: "Khởi động lại MuMu" }));

    expect(
      within(tab).getByText("MuMu đang mở nên chưa đổi được màn hình. Cần khởi động lại MuMu."),
    ).toBeInTheDocument();
    await waitFor(async () =>
      expect(await bodies(fetch, "POST /api/setup/auto")).toEqual([
        { restart_mumu: false },
        { restart_mumu: true },
      ]),
    );
  });

  it("waits while a run holds the emulator", async () => {
    renderSetup(
      overview({ running: { trigger: "setup", pid: 4242, since: "10:00:00", runs: [] } }),
    );

    const tab = await setupTab();
    expect(within(tab).getByRole("button", { name: "Thiết lập tự động" })).toBeDisabled();
    expect(
      within(tab).getByText("Chạy thử và Thiết lập tự động tạm khóa cho tới khi xong"),
    ).toBeInTheDocument();
  });

  it("says why it could not run", async () => {
    const held = reply({ error: "lock_held", detail: "Another run is in progress" }, 409);
    renderSetup(overview(), { "POST /api/setup/auto": held });
    const tab = await setupTab();

    fireEvent.click(within(tab).getByRole("button", { name: "Thiết lập tự động" }));

    expect(
      await within(tab).findByText("Đang có một lần chạy khác. Hãy chờ nó xong rồi thử lại."),
    ).toBeInTheDocument();
  });
});

describe("SetupTab options and guide", () => {
  it("switches the notification at once, in the UI's language", async () => {
    const { fetch, replies } = renderSetup();
    const tab = await setupTab();
    replies["PUT /api/notifications"] = reply({ enabled: false, language: "vi" });
    const toggle = await within(tab).findByRole("switch", { name: "Thông báo kết quả" });
    expect(toggle).toHaveAttribute("aria-checked", "true");

    fireEvent.click(toggle);

    await waitFor(async () =>
      expect(await bodies(fetch, "PUT /api/notifications")).toEqual([
        { enabled: false, language: "vi" },
      ]),
    );
    expect(within(tab).queryByRole("button", { name: "Gửi thử" })).not.toBeInTheDocument();
  });

  it("opens a guide row on a press", async () => {
    renderSetup();
    const tab = await setupTab();
    const morning = within(tab).getByText("Mỗi sáng diễn ra thế nào").closest("details");
    expect(morning).not.toHaveAttribute("open");

    fireEvent.click(within(tab).getByText("Mỗi sáng diễn ra thế nào"));

    expect(morning).toHaveAttribute("open");
    expect(morning).toHaveTextContent(
      "05:50 máy tự thức dậy, mở MuMu và app Vinhomes. 06:00 đặt các khung đã chọn",
    );
    const trouble = within(tab).getByText("Khi có sự cố").closest("details");
    expect(trouble).toHaveTextContent('Báo "Hết chỗ"Khung đó có người đặt trước.');
  });
});
