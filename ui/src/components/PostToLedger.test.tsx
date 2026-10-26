import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PostToLedger } from "./PostToLedger";

describe("PostToLedger", () => {
  it("disables post for REVIEW and BLOCK", () => {
    const { rerender } = render(
      <PostToLedger
        outcome="REVIEW"
        posted={false}
        entry={null}
        onPost={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: /post to ledger/i })).toBeDisabled();

    rerender(
      <PostToLedger
        outcome="BLOCK"
        posted={false}
        entry={null}
        onPost={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: /post to ledger/i })).toBeDisabled();
  });

  it("enables post for ALLOW", () => {
    render(
      <PostToLedger
        outcome="ALLOW"
        posted={false}
        entry={null}
        onPost={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: /post to ledger/i })).toBeEnabled();
  });
});
