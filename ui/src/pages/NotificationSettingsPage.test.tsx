import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { NotificationSettings } from "../api/types";
import { paths } from "../paths";
import { renderApp } from "../test/app";
import { type Reply, reply, requestsTo } from "../test/backend";

function renderNotifications(
  saved: NotificationSettings = { enabled: true, language: "vi" },
  extra: Record<string, Reply> = {},
) {
  const replies: Record<string, Reply> = {
    "GET /api/notifications": reply(saved),
    ...extra,
  };
  return { replies, ...renderApp(paths.notificationSettings, replies) };
}

/** The bodies of the PUT requests the page sent, in order. */
async function putBodies(fetch: ReturnType<typeof renderNotifications>["fetch"]) {
  const puts = fetch.mock.calls.map(([request]) => request).filter((r) => r.method === "PUT");
  return Promise.all(puts.map((request) => request.clone().json() as Promise<unknown>));
}

function windowsSwitch() {
  return screen.findByRole("switch", { name: "Thông báo Windows" });
}

describe("NotificationSettingsPage", () => {
  it("is the third tab of Settings and shows the saved switch", async () => {
    renderNotifications();

    const tabs = screen.getByRole("navigation", { name: "Phần cài đặt" });
    expect(within(tabs).getByRole("link", { name: "Thông báo" })).toHaveAttribute(
      "href",
      paths.notificationSettings,
    );
    expect(await windowsSwitch()).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText(/góc màn hình hiện ngày chơi/)).toBeInTheDocument();
  });

  it("saves the switch at once, with the UI's language", async () => {
    const { fetch } = renderNotifications(
      { enabled: true, language: "en" },
      { "PUT /api/notifications": reply({ enabled: false, language: "vi" }) },
    );

    fireEvent.click(await windowsSwitch());

    await waitFor(async () =>
      expect(await windowsSwitch()).toHaveAttribute("aria-checked", "false"),
    );
    expect(await putBodies(fetch)).toEqual([{ enabled: false, language: "vi" }]);
  });

  it("says why the switch was not saved", async () => {
    const refused = reply({ error: "bad_request", detail: "Invalid configuration" }, 400);
    renderNotifications(undefined, { "PUT /api/notifications": refused });

    fireEvent.click(await windowsSwitch());

    expect(await screen.findByText("Chưa làm được việc này lúc này.")).toBeInTheDocument();
    expect(await windowsSwitch()).toHaveAttribute("aria-checked", "true");
  });

  it("sends a test notification and says where to look", async () => {
    const { fetch } = renderNotifications(undefined, {
      "POST /api/notifications/test": reply(null, 204),
    });

    fireEvent.click(await screen.findByRole("button", { name: "Gửi thử" }));

    expect(await screen.findByText("Đã gửi. Xem góc phải dưới màn hình.")).toBeInTheDocument();
    expect(requestsTo(fetch, "POST /api/notifications/test")).toBe(1);
    expect(requestsTo(fetch, "PUT /api/notifications")).toBe(0);
  });

  it("gives the test the UI's language first when the saved one differs", async () => {
    const { fetch } = renderNotifications(
      { enabled: true, language: "en" },
      {
        "PUT /api/notifications": reply({ enabled: true, language: "vi" }),
        "POST /api/notifications/test": reply(null, 204),
      },
    );

    fireEvent.click(await screen.findByRole("button", { name: "Gửi thử" }));

    expect(await screen.findByText("Đã gửi. Xem góc phải dưới màn hình.")).toBeInTheDocument();
    expect(await putBodies(fetch)).toEqual([{ enabled: true, language: "vi" }]);
    const order = fetch.mock.calls.map(([request]) => request.method);
    expect(order.lastIndexOf("PUT")).toBeLessThan(order.lastIndexOf("POST"));
  });

  it("says when Windows did not show the test", async () => {
    const failed = reply({ error: "notification", detail: "not shown" }, 503);
    renderNotifications(undefined, { "POST /api/notifications/test": failed });

    fireEvent.click(await screen.findByRole("button", { name: "Gửi thử" }));

    expect(await screen.findByText("Windows không hiện được thông báo.")).toBeInTheDocument();
  });
});
