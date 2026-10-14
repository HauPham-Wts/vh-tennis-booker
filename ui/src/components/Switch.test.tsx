import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import { Switch } from "./Switch";

describe("Switch", () => {
  it("is a named switch that shows and announces its state", () => {
    render(<Switch label="Hẹn giờ mỗi sáng" checked onChange={() => undefined} />);

    const control = screen.getByRole("switch", { name: "Hẹn giờ mỗi sáng" });
    expect(control).toBeChecked();
    expect(control).toHaveTextContent("Đang bật");
  });

  it("asks for the other state when clicked", () => {
    const onChange = vi.fn();
    render(<Switch label="Hẹn giờ mỗi sáng" checked={false} onChange={onChange} />);

    const control = screen.getByRole("switch", { name: "Hẹn giờ mỗi sáng" });
    expect(control).not.toBeChecked();
    expect(control).toHaveTextContent("Đang tắt");
    fireEvent.click(control);

    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("writes its state in English and takes other words", async () => {
    await act(() => i18n.changeLanguage("en"));
    const { rerender } = render(<Switch label="Daily" checked onChange={() => undefined} />);
    expect(screen.getByRole("switch", { name: "Daily" })).toHaveTextContent("On");

    rerender(<Switch label="Daily" checked onText="Booking daily" onChange={() => undefined} />);
    expect(screen.getByRole("switch", { name: "Daily" })).toHaveTextContent("Booking daily");
  });

  it("ignores clicks while disabled", () => {
    const onChange = vi.fn();
    render(<Switch label="Hẹn giờ mỗi sáng" checked disabled onChange={onChange} />);

    fireEvent.click(screen.getByRole("switch", { name: "Hẹn giờ mỗi sáng" }));

    expect(onChange).not.toHaveBeenCalled();
  });
});
