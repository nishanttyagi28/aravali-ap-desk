import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { PdfViewer } from "./PdfViewer";

function ViewerHarness() {
  const [page, setPage] = useState(1);
  return (
    <PdfViewer
      file={null}
      pageNumber={page}
      pageCount={3}
      onPageChange={setPage}
      fields={[
        {
          name: "a",
          bbox: { page: 2, x0: 0, y0: 0, x1: 10, y1: 10 },
          confidence: 1,
        },
      ]}
      highlighted={null}
      onHighlight={() => {}}
    />
  );
}

describe("PdfViewer multipage", () => {
  it("renders pager and switches pages", async () => {
    const user = userEvent.setup();
    render(<ViewerHarness />);

    expect(screen.getByRole("button", { name: /page 1/i })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await user.click(screen.getByRole("button", { name: /page 2/i }));
    expect(screen.getByRole("button", { name: /page 2/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
