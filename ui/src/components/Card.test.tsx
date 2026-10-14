import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Card } from "./Card";

describe("Card", () => {
  it("is a div unless told otherwise", () => {
    render(<Card data-testid="card">Nội dung</Card>);

    expect(screen.getByTestId("card").tagName).toBe("DIV");
  });

  it("can be a section named by its heading", () => {
    render(
      <Card as="section" aria-labelledby="slots" shadow>
        <h2 id="slots">Khung giờ muốn đặt</h2>
      </Card>,
    );

    expect(screen.getByRole("region", { name: "Khung giờ muốn đặt" }).tagName).toBe("SECTION");
  });

  it("can be a list item", () => {
    render(
      <ul>
        <Card as="li">Chơi Thứ Tư 14/10</Card>
      </ul>,
    );

    expect(screen.getByRole("listitem")).toHaveTextContent("Chơi Thứ Tư 14/10");
  });
});
