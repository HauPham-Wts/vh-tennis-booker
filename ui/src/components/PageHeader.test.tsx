import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PageHeader } from "./PageHeader";

describe("PageHeader", () => {
  it("shows the title, the lead and the controls, and names the window", async () => {
    render(
      <PageHeader title="Nhật ký" lead="Từng bước app đã làm.">
        <button type="button">Tất cả</button>
      </PageHeader>,
    );

    expect(screen.getByRole("heading", { level: 1, name: "Nhật ký" })).toBeInTheDocument();
    expect(screen.getByText("Từng bước app đã làm.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tất cả" })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe("Nhật ký · Court Booker"));
  });

  it("leaves out what it is not given", () => {
    const { container } = render(<PageHeader title="Hướng dẫn" />);

    expect(container.querySelectorAll("p")).toHaveLength(0);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
