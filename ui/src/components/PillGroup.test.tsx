import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PillGroup } from "./PillGroup";

const OPTIONS = [
  { value: "all", label: "Tất cả" },
  { value: "slot", label: "Đặt sân" },
  { value: "error", label: "Có lỗi" },
] as const;

describe("PillGroup", () => {
  it("names the group and presses the chosen option only", () => {
    render(
      <PillGroup label="Lọc theo loại" options={OPTIONS} value="slot" onChange={() => undefined} />,
    );

    expect(screen.getByRole("group", { name: "Lọc theo loại" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Đặt sân" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Tất cả" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Có lỗi" })).toHaveAttribute("aria-pressed", "false");
  });

  it("reports the option clicked", () => {
    const onChange = vi.fn();
    render(<PillGroup label="Lọc theo loại" options={OPTIONS} value="all" onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Có lỗi" }));

    expect(onChange).toHaveBeenCalledWith("error");
  });
});
