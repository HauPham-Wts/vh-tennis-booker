import { useQuery } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { createTestQueryClient, withQueryClient } from "../test/queries";
import { QueryView } from "./QueryView";

const LOCK_HELD = new ApiError(409, { error: "lock_held", detail: "A run holds the lock" });

/** Show the runs a read gives, with "Chưa có lần chạy nào" for none. */
function Runs({ read }: { read: () => Promise<string[]> }) {
  const query = useQuery({ queryKey: ["runs"], queryFn: read });
  return (
    <>
      {/* Shows when the component has seen the query's latest state. */}
      <span data-testid="status">{query.status}</span>
      <QueryView query={query} isEmpty={(runs) => runs.length === 0} empty="Chưa có lần chạy nào">
        {(runs) => <p>{runs.join(", ")}</p>}
      </QueryView>
    </>
  );
}

function renderRuns(read: () => Promise<string[]>) {
  const client = createTestQueryClient();
  const Wrapper = withQueryClient(client);
  render(
    <Wrapper>
      <Runs read={read} />
    </Wrapper>,
  );
  return client;
}

describe("QueryView", () => {
  it("says it is loading until the data comes", async () => {
    let answer: (runs: string[]) => void = () => undefined;
    renderRuns(() => new Promise((resolve) => (answer = resolve)));

    expect(screen.getByRole("status")).toHaveTextContent("Đang tải…");
    answer(["12/10", "11/10"]);

    expect(await screen.findByText("12/10, 11/10")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("says when there is nothing to show", async () => {
    renderRuns(() => Promise.resolve([]));

    expect(await screen.findByText("Chưa có lần chạy nào")).toBeInTheDocument();
  });

  it("explains an error and tries again on request", async () => {
    const read = vi.fn<() => Promise<string[]>>().mockRejectedValueOnce(LOCK_HELD);
    read.mockResolvedValueOnce(["12/10"]);
    renderRuns(read);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Đang có một lần chạy khác. Hãy chờ nó xong rồi thử lại.");
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));

    expect(await screen.findByText("12/10")).toBeInTheDocument();
    expect(read).toHaveBeenCalledTimes(2);
  });

  it("keeps the data shown when a later refresh fails", async () => {
    const read = vi.fn<() => Promise<string[]>>().mockResolvedValueOnce(["12/10"]);
    read.mockRejectedValueOnce(LOCK_HELD);
    const client = renderRuns(read);
    await screen.findByText("12/10");

    await act(() => client.refetchQueries({ queryKey: ["runs"] }));

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("error"));
    expect(read).toHaveBeenCalledTimes(2);
    expect(screen.getByText("12/10")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
