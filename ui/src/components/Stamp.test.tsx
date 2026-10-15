import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Stamp } from "./Stamp";

describe("Stamp", () => {
  it("shows its words as plain text", () => {
    render(
      <p>
        18:00–19:00 <Stamp>ĐÃ ĐẶT</Stamp>
      </p>,
    );

    expect(screen.getByText("ĐÃ ĐẶT")).toBeInTheDocument();
    expect(screen.getByText("ĐÃ ĐẶT").closest("p")).toHaveTextContent("18:00–19:00 ĐÃ ĐẶT");
  });

  it("marks a failure with its own tone", () => {
    render(<Stamp tone="failed">KHÔNG ĐẶT ĐƯỢC</Stamp>);

    expect(screen.getByText("KHÔNG ĐẶT ĐƯỢC").className).toMatch(/failed/);
  });
});
