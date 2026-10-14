import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Ticket } from "./Ticket";

describe("Ticket", () => {
  it("shows the main part and the stub, with the notches hidden from screen readers", () => {
    const { container } = render(
      <Ticket as="section" aria-labelledby="next-run" stub={<p>Thứ Năm 15/10</p>}>
        <h2 id="next-run">Lần đặt tiếp theo</h2>
        <p>06:00</p>
      </Ticket>,
    );

    const ticket = screen.getByRole("region", { name: "Lần đặt tiếp theo" });
    expect(ticket).toHaveTextContent("06:00");
    expect(ticket).toHaveTextContent("Thứ Năm 15/10");
    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(2);
  });

  it("can be a list item of a ledger of tickets", () => {
    render(
      <ol>
        <Ticket as="li" notch="small" stub="ĐÃ ĐẶT 2/2">
          Chơi Thứ Tư 14/10
        </Ticket>
      </ol>,
    );

    expect(screen.getByRole("listitem")).toHaveTextContent("Chơi Thứ Tư 14/10ĐÃ ĐẶT 2/2");
  });
});
