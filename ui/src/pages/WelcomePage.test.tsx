import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Overview, SetupItem } from "../api/types";
import i18n from "../i18n";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { type Reply, reply } from "../test/backend";
import { overview } from "../test/overview";
import { settings } from "../test/settings";
import { welcomeShown } from "../welcome";

/** An app not used yet whose PC wakes at 05:40 and books at 06:00. */
function unused(): Overview {
  const status = overview();
  return overview({
    schedule: { ...status.schedule, enabled: false, dry_run_passed: false, wake_at: "05:40" },
  });
}

function renderWelcome(path: string = paths.welcome, extra: Record<string, Reply> = {}) {
  return renderApp(path, { "GET /api/status": reply(unused()), ...extra });
}

function stepBar() {
  return screen.findByRole("navigation", { name: "Các bước bắt đầu" });
}

describe("WelcomePage step bar", () => {
  it("lists the four steps with the first one current", async () => {
    renderWelcome();

    const links = within(await stepBar()).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([
      "1 · Giới thiệu",
      "2 · Thiết lập máy",
      "3 · Chọn khung giờ",
      "4 · Hẹn giờ",
    ]);
    expect(links[0]).toHaveAttribute("aria-current", "step");
    expect(links[1]).not.toHaveAttribute("aria-current");
    expect(links[2]).toHaveAttribute("href", `${paths.welcome}?step=3`);
  });

  it("opens the step the address names", async () => {
    renderWelcome(`${paths.welcome}?step=3`);

    const bar = await stepBar();
    expect(within(bar).getByRole("link", { name: "3 · Chọn khung giờ" })).toHaveAttribute(
      "aria-current",
      "step",
    );
  });

  it.each(["0", "5", "two", ""])("opens the first step for step=%s", async (value) => {
    renderWelcome(`${paths.welcome}?step=${value}`);

    const bar = await stepBar();
    expect(within(bar).getByRole("link", { name: "1 · Giới thiệu" })).toHaveAttribute(
      "aria-current",
      "step",
    );
  });

  it("names the window and hides the main navigation", async () => {
    renderWelcome();

    await stepBar();
    await waitFor(() => expect(document.title).toBe("Chào mừng · Court Booker"));
    expect(screen.queryByRole("navigation", { name: "Điều hướng chính" })).not.toBeInTheDocument();
  });

  it("marks the welcome screen as shown", async () => {
    renderWelcome();

    await stepBar();
    expect(welcomeShown()).toBe(true);
  });
});

describe("WelcomePage introduction", () => {
  it("tells what happens every morning with this PC's times", async () => {
    renderWelcome();

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Đặt sân tennis lúc 06:00, kể cả khi bạn đang ngủ",
      }),
    ).toBeInTheDocument();
    const morning = screen.getByRole("region", { name: "Mỗi sáng diễn ra thế nào" });
    const moments = within(morning).getAllByRole("listitem");
    expect(moments.map((moment) => moment.textContent)).toEqual([
      "05:40Máy tính tự thức dậyTừ chế độ Sleep, không cần bạn bật.",
      "Ngay sau đóMở MuMu và app VinhomesRồi chờ sẵn ở mục Sân Tennis.",
      "06:00Đặt các khung giờ bạn chọnHai khung giờ thường xong trong khoảng 15 giây, rồi MuMu tự đóng.",
    ]);
  });

  it("says what to prepare and that passwords stay out of reach", async () => {
    renderWelcome();

    const need = await screen.findByRole("region", { name: "Bạn cần chuẩn bị" });
    const items = within(need).getAllByRole("listitem");
    expect(items.map((item) => item.querySelector("strong")?.textContent)).toEqual([
      "MuMu Player",
      "App Vinhomes Resident",
      "Tài khoản cư dân Vinhomes",
    ]);
    expect(need).toHaveTextContent("không bao giờ đọc hay lưu mật khẩu");
  });

  it("goes on to the device setup and brings its step into view", async () => {
    const { router } = renderWelcome();

    fireEvent.click(await screen.findByRole("link", { name: "Bắt đầu thiết lập" }));

    expect(
      await screen.findByRole("heading", { level: 1, name: "Thiết lập máy" }),
    ).toBeInTheDocument();
    expect(router.state.location.search).toBe("?step=2");
    const bar = await stepBar();
    expect(within(bar).getByRole("link", { name: "2 · Thiết lập máy" })).toHaveFocus();
  });

  it("leaves the focus alone when the screen opens", async () => {
    renderWelcome();

    await screen.findByRole("link", { name: "Bắt đầu thiết lập" });
    expect(document.body).toHaveFocus();
  });
});

describe("WelcomePage moves", () => {
  it("offers only a way out on the first step", async () => {
    renderWelcome();

    await screen.findByRole("link", { name: "Bắt đầu thiết lập" });
    expect(screen.getByRole("link", { name: "Để sau" })).toHaveAttribute("href", paths.overview);
    expect(screen.queryByRole("link", { name: "Quay lại" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Tiếp" })).not.toBeInTheDocument();
  });

  it("goes back and on between the middle steps", async () => {
    renderWelcome(`${paths.welcome}?step=2`);

    expect(await screen.findByRole("link", { name: "Quay lại" })).toHaveAttribute(
      "href",
      `${paths.welcome}?step=1`,
    );
    expect(screen.getByRole("link", { name: "Tiếp" })).toHaveAttribute(
      "href",
      `${paths.welcome}?step=3`,
    );
    expect(screen.getByRole("link", { name: "Để sau" })).toHaveAttribute("href", paths.overview);
  });

  it("ends on the Overview after the last step", async () => {
    const { router } = renderWelcome(`${paths.welcome}?step=4`);

    fireEvent.click(await screen.findByRole("link", { name: "Xong, về Tổng quan" }));

    // Already shown in this opening, so the Overview stays.
    expect(await screen.findByRole("heading", { level: 1, name: "Tổng quan" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(paths.overview);
  });

  it("lets the user leave and stay on the Overview", async () => {
    const { router } = renderWelcome();

    fireEvent.click(await screen.findByRole("link", { name: "Để sau" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Tổng quan" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(paths.overview);
  });
});

describe("WelcomePage in English", () => {
  it("speaks English", async () => {
    await act(() => i18n.changeLanguage("en"));
    renderWelcome();

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Book a tennis court at 06:00, even while you sleep",
      }),
    ).toBeInTheDocument();
    const bar = screen.getByRole("navigation", { name: "Getting started" });
    expect(within(bar).getByRole("link", { name: "2 · Device setup" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Start the setup" })).toBeInTheDocument();
  });
});

describe("WelcomePage steps 2 to 4", () => {
  /** Every check passed, as GET /api/setup gives it. */
  const CHECKS: SetupItem[] = ["mumu_installed", "mumu_screen", "wake_timers", "app_installed"].map(
    (item) => ({ item, status: "ok", detail: "" }),
  );

  function renderStep(step: number) {
    return renderWelcome(`${paths.welcome}?step=${step}`, {
      "GET /api/setup": reply(CHECKS),
      "GET /api/settings": reply(settings()),
      "PUT /api/settings": reply(settings({ slots: ["07:00 - 08:00"] })),
      "GET /api/schedule": reply(unused().schedule),
      "GET /api/runs": reply([]),
    });
  }

  function nextLink() {
    return screen.findByRole("link", { name: "Tiếp" });
  }

  it("sets up the device on step 2 as Settings does", async () => {
    renderStep(2);

    const title = await screen.findByRole("heading", { level: 1, name: "Thiết lập máy" });
    // The title and the lead form a group of their own, as close as on step 4.
    const group = title.parentElement;
    expect(group?.children).toHaveLength(2);
    expect(group).toContainElement(screen.getByText("Chuẩn bị máy tính một lần", { exact: false }));
    expect(await screen.findByRole("heading", { name: "Việc bạn cần làm" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Thiết lập tự động" })).toBeInTheDocument();
  });

  it("chooses the slots on step 3 as Settings does", async () => {
    renderStep(3);

    expect(
      await screen.findByRole("heading", { level: 1, name: "Chọn ngày, sân và khung giờ" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("group", { name: "Buổi sáng" })).toBeInTheDocument();
    expect(await nextLink()).toHaveAttribute("href", `${paths.welcome}?step=4`);
  });

  it("holds Tiếp back while chosen slots are not saved", async () => {
    renderStep(3);
    await screen.findByRole("group", { name: "Buổi sáng" });

    fireEvent.click(screen.getByRole("button", { name: "15:00–16:00, lượt 1" }));

    const next = screen.getByRole("button", { name: "Tiếp" });
    expect(next).toBeDisabled();
    expect(next).toHaveAccessibleDescription('Bấm "Lưu thay đổi" hoặc "Hủy" trước khi tiếp.');

    fireEvent.click(screen.getByRole("button", { name: "Hủy" }));

    expect(await nextLink()).toBeInTheDocument();
  });

  it("lets the user go on once the slots are saved", async () => {
    renderStep(3);
    await screen.findByRole("group", { name: "Buổi sáng" });
    fireEvent.click(screen.getByRole("button", { name: "15:00–16:00, lượt 1" }));

    fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));

    expect(await nextLink()).toBeInTheDocument();
    expect(screen.queryByText(/trước khi tiếp/)).not.toBeInTheDocument();
  });

  it("forgets a draft left behind on another step", async () => {
    renderStep(3);
    await screen.findByRole("group", { name: "Buổi sáng" });
    fireEvent.click(screen.getByRole("button", { name: "15:00–16:00, lượt 1" }));

    fireEvent.click(screen.getByRole("link", { name: "4 · Hẹn giờ" }));

    expect(await screen.findByRole("link", { name: "Xong, về Tổng quan" })).toBeInTheDocument();
  });

  it("runs the dry run and switches the schedule on step 4 as the Schedule screen does", async () => {
    renderStep(4);

    expect(await screen.findByRole("heading", { level: 1, name: "Hẹn giờ" })).toBeInTheDocument();
    expect(
      await screen.findByText(
        "Chạy thử một lần cho chắc, rồi bật hẹn giờ để app tự đặt sân lúc 06:00 mỗi sáng.",
      ),
    ).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Chạy thử ngay" })).toBeInTheDocument();
    expect(await screen.findByRole("switch", { name: "Hẹn giờ mỗi sáng" })).toBeDisabled();
  });
});
