import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
  it("is a plain button that reports clicks", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Chạy thử ngay</Button>);

    const button = screen.getByRole("button", { name: "Chạy thử ngay" });
    fireEvent.click(button);

    expect(button).toHaveAttribute("type", "button");
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("can submit a form when asked", () => {
    render(
      <Button type="submit" variant="primary">
        Lưu thay đổi
      </Button>,
    );

    expect(screen.getByRole("button", { name: "Lưu thay đổi" })).toHaveAttribute("type", "submit");
  });

  it("ignores clicks while disabled", () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Chạy thử ngay
      </Button>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Chạy thử ngay" }));

    expect(screen.getByRole("button", { name: "Chạy thử ngay" })).toBeDisabled();
    expect(onClick).not.toHaveBeenCalled();
  });
});
