import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import i18n from "../i18n";
import { paths } from "../paths";
import { renderApp } from "../test/app";

function renderGuide() {
  return renderApp(paths.guide);
}

/** The disclosure that a question of "Khi có sự cố" opens. */
function trouble(question: string): HTMLDetailsElement {
  const details = screen.getByText(question).closest("details");
  if (details === null) {
    throw new Error(`No question "${question}"`);
  }
  return details;
}

describe("GuidePage", () => {
  it("sends no request", async () => {
    const { fetch } = renderGuide();

    expect(await screen.findByRole("heading", { level: 1, name: "Hướng dẫn" })).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("links back to the introduction", () => {
    renderGuide();

    expect(screen.getByText("Cách dùng từng phần của Court Booker.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Xem lại phần giới thiệu" })).toHaveAttribute(
      "href",
      paths.welcome,
    );
  });

  it("links each of the four steps to the screen where it is done", () => {
    renderGuide();

    const steps = screen.getByRole("region", { name: "Bắt đầu trong 4 bước" });
    const links = within(steps).getAllByRole("link");
    expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["1Thiết lập máyCài đặt › Thiết lập máy", paths.deviceSetup],
      ["2Chọn khung giờ và sânCài đặt › Đặt sân", paths.bookingSettings],
      ["3Chạy thửHẹn giờ › Chạy thử ngay", paths.schedule],
      ["4Bật hẹn giờHẹn giờ › Hẹn giờ mỗi sáng", paths.schedule],
    ]);
  });

  it("opens a step's screen", async () => {
    const { router } = renderGuide();

    fireEvent.click(screen.getByRole("link", { name: /Chọn khung giờ và sân/ }));

    expect(await screen.findByRole("heading", { level: 1, name: "Cài đặt" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(paths.bookingSettings);
  });

  it("describes each screen of the menu, quoting its labels", () => {
    renderGuide();

    const list = screen.getByRole("region", { name: "Từng màn hình" });
    const names = within(list)
      .getAllByRole("term")
      .map((term) => term.textContent);
    expect(names).toEqual(["Tổng quan", "Hẹn giờ", "Lịch sử", "Cài đặt"]);
    expect(
      within(list).getByText(/^"Lịch sử": .* "Nhật ký": .* mở "Chi tiết kỹ thuật"/),
    ).toBeInTheDocument();
    expect(within(list).getByText(/^"Đặt sân": .* "Thiết lập máy": /)).toBeInTheDocument();
  });

  it("opens the answer of a problem when its question is pressed", () => {
    renderGuide();

    const details = trouble('Kết quả báo "Hết chỗ"');
    expect(details.open).toBe(false);

    fireEvent.click(screen.getByText('Kết quả báo "Hết chỗ"'));

    expect(details.open).toBe(true);
    expect(within(details).getByText(/khung giờ khác ở Cài đặt › Đặt sân\.$/)).toBeVisible();
  });

  it("names the buttons and results as the other screens show them", () => {
    renderGuide();

    expect(trouble('Thiết lập máy báo "CHƯA XONG"')).toHaveTextContent(
      'bấm "Kiểm tra lại". Với các mục Court Booker tự làm, bấm "Thiết lập tự động".',
    );
    expect(trouble("App Vinhomes bị đăng xuất")).toHaveTextContent(
      'Kết quả báo "App Vinhomes chưa mở được, có thể đã bị đăng xuất".',
    );
  });

  it("speaks English", async () => {
    await i18n.changeLanguage("en");
    renderGuide();

    expect(await screen.findByRole("heading", { level: 1, name: "Guide" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Do a dry run/ })).toHaveTextContent(
      "Schedule › Dry run now",
    );
    expect(trouble('The result says "Fully booked"')).toHaveTextContent(
      "other slots in Settings › Booking.",
    );
  });
});
