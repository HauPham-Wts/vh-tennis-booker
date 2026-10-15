import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Ledger } from "./Ledger";

describe("Ledger", () => {
  it("is a named table inside a named scroll area that takes focus", () => {
    render(
      <Ledger label="Lịch sử gần đây">
        <thead>
          <tr>
            <th scope="col">Thời điểm</th>
            <th scope="col">Kết quả</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>12/10 06:00</td>
            <td>✓ 2/2</td>
          </tr>
        </tbody>
      </Ledger>,
    );

    const area = screen.getByRole("region", { name: "Lịch sử gần đây" });
    expect(area).toHaveAttribute("tabindex", "0");
    const table = within(area).getByRole("table", { name: "Lịch sử gần đây" });
    expect(within(table).getByRole("columnheader", { name: "Kết quả" })).toBeInTheDocument();
    expect(within(table).getByRole("cell", { name: "✓ 2/2" })).toBeInTheDocument();
  });
});
