import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Settings } from "../api/types";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { reply, type Reply } from "../test/backend";
import { settings } from "../test/settings";

function renderBooking(saved: Settings = settings(), put: Reply = reply(saved)) {
  return renderApp(paths.bookingSettings, {
    "GET /api/settings": reply(saved),
    "PUT /api/settings": put,
  });
}

/** The body of the one PUT the page sent. */
async function savedBody(fetch: ReturnType<typeof renderBooking>["fetch"]): Promise<Settings> {
  const put = fetch.mock.calls.map(([request]) => request).find((r) => r.method === "PUT");
  expect(put).toBeDefined();
  return (await put?.json()) as Settings;
}

function slot(name: string | RegExp) {
  return screen.getByRole("button", { name });
}

function saveButton() {
  return screen.getByRole("button", { name: "Lưu thay đổi" });
}

describe("BookingSettingsPage", () => {
  it("shows the saved slots in booking order, the court and the day", async () => {
    renderBooking(settings({ slots: ["16:00 - 17:00", "15:00 - 16:00"] }));

    expect(await screen.findByRole("button", { name: "16:00–17:00, lượt 1" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(slot("15:00–16:00, lượt 2")).toHaveAttribute("aria-pressed", "true");
    expect(slot("18:00–19:00")).toHaveAttribute("aria-pressed", "false");
    const morning = screen.getByRole("group", { name: "Buổi sáng" });
    expect(within(morning).getAllByRole("button")).toHaveLength(6);
    expect(screen.getByRole("combobox", { name: "Sân" })).toHaveDisplayValue("S6");
    const day = screen.getByRole("combobox", { name: "Đặt cho ngày" });
    expect(day).toHaveDisplayValue("Ngày kia");
    expect(day).toHaveAccessibleDescription("App mở đặt sân trước tối đa 2 ngày.");
  });

  it("saves the new choice with the developer's settings as they were", async () => {
    const after = settings({
      slots: ["16:00 - 17:00", "07:00 - 08:00"],
      court: "S9 - Sân tennis",
    });
    const { fetch } = renderBooking(settings(), reply(after));
    await screen.findByRole("group", { name: "Buổi sáng" });
    expect(saveButton()).toBeDisabled();

    fireEvent.click(slot(/^15:00–16:00/));
    fireEvent.click(slot("07:00–08:00"));
    fireEvent.change(screen.getByRole("combobox", { name: "Sân" }), {
      target: { value: "S9 - Sân tennis" },
    });
    fireEvent.click(saveButton());

    expect(await screen.findByText("Đã lưu. Áp dụng từ lần đặt tiếp theo.")).toBeInTheDocument();
    expect(await savedBody(fetch)).toEqual(after);
    expect(slot("07:00–08:00, lượt 2")).toHaveAttribute("aria-pressed", "true");
    expect(saveButton()).toBeDisabled();
  });

  it("goes back to the saved choice on cancel", async () => {
    renderBooking();
    fireEvent.click(await screen.findByRole("button", { name: "18:00–19:00" }));
    expect(slot("18:00–19:00, lượt 3")).toBeInTheDocument();

    fireEvent.click(slot("Hủy"));

    expect(slot("18:00–19:00")).toHaveAttribute("aria-pressed", "false");
    expect(slot("Hủy")).toBeDisabled();
  });

  it("asks for a slot before saving", async () => {
    renderBooking();
    fireEvent.click(await screen.findByRole("button", { name: /^15:00–16:00/ }));
    fireEvent.click(slot(/^16:00–17:00/));

    expect(screen.getByText("Chọn ít nhất một khung giờ.")).toBeInTheDocument();
    expect(saveButton()).toBeDisabled();
  });

  it("says why a save failed and keeps the draft", async () => {
    const problem = { error: "invalid_settings", detail: "court is empty", problems: [] };
    renderBooking(settings(), reply(problem, 422));
    fireEvent.click(await screen.findByRole("button", { name: "18:00–19:00" }));

    fireEvent.click(saveButton());

    expect(await screen.findByText("Một số cài đặt chưa hợp lệ.")).toBeInTheDocument();
    expect(slot("18:00–19:00, lượt 3")).toHaveAttribute("aria-pressed", "true");
  });

  it("keeps a court and a slot the developer set by hand", async () => {
    renderBooking(settings({ court: "S1 - Sân tennis", slots: ["12:00 - 13:00"] }));

    const court = await screen.findByRole("combobox", { name: "Sân" });
    expect(court).toHaveDisplayValue("S1");
    expect(within(court).getAllByRole("option")).toHaveLength(5);
    const afternoon = screen.getByRole("group", { name: "Buổi chiều · tối" });
    expect(within(afternoon).getByRole("button", { name: "12:00–13:00, lượt 1" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
