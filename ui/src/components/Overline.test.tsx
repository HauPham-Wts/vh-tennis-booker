import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Overline } from "./Overline";

describe("Overline", () => {
  it("can name a section as its heading", () => {
    render(
      <section aria-labelledby="next-run">
        <Overline as="h2" id="next-run">
          Lần đặt tiếp theo
        </Overline>
      </section>,
    );

    expect(
      screen.getByRole("heading", { level: 2, name: "Lần đặt tiếp theo" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Lần đặt tiếp theo" })).toBeInTheDocument();
  });

  it("can name a value in a description list", () => {
    render(
      <dl>
        <Overline as="dt">Ngày chơi</Overline>
        <dd>Thứ Năm 15/10</dd>
      </dl>,
    );

    expect(screen.getByRole("term")).toHaveTextContent("Ngày chơi");
  });
});
