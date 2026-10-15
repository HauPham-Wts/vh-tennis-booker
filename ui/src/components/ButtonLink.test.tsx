import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { ButtonLink } from "./ButtonLink";

describe("ButtonLink", () => {
  it("is a link to another screen", () => {
    const router = createMemoryRouter([
      { path: "/", element: <ButtonLink to="/welcome">Xem lại phần giới thiệu</ButtonLink> },
    ]);
    render(<RouterProvider router={router} />);

    expect(screen.getByRole("link", { name: "Xem lại phần giới thiệu" })).toHaveAttribute(
      "href",
      "/welcome",
    );
  });
});
