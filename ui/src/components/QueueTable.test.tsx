import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueueTable, type QueueFilters } from "./QueueTable";
import type { ReviewQueueItem } from "../api/client";

const items: ReviewQueueItem[] = [
  {
    invoice_id: "11111111-1111-1111-1111-111111111111",
    vendor_name: "Vendor A",
    vendor_gstin: "27YTCVR4268P1ZW",
    invoice_number: "INV-1",
    invoice_date: "2025-01-01",
    grand_total: "1000.00",
    outcome: "ALLOW",
    issue_count: 0,
    top_issue_code: null,
    posted: false,
  },
  {
    invoice_id: "22222222-2222-2222-2222-222222222222",
    vendor_name: "Vendor B",
    vendor_gstin: null,
    invoice_number: "INV-2",
    invoice_date: "2025-01-02",
    grand_total: "2000.00",
    outcome: "BLOCK",
    issue_count: 1,
    top_issue_code: "LINE_ARITHMETIC",
    posted: false,
  },
];

function renderTable(
  filters: QueueFilters,
  onChange: (f: QueueFilters) => void,
) {
  return render(
    <MemoryRouter>
      <QueueTable
        items={items}
        filters={filters}
        onFiltersChange={onChange}
      />
    </MemoryRouter>,
  );
}

describe("QueueTable filters", () => {
  it("toggles decision filter", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderTable({ decision: [], issue_code: [] }, onChange);

    await user.click(screen.getByLabelText("BLOCK", { selector: "input" }));
    expect(onChange).toHaveBeenCalledWith({
      decision: ["BLOCK"],
      issue_code: [],
    });
  });

  it("filters issue code via select", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderTable({ decision: [], issue_code: [] }, onChange);

    await user.selectOptions(
      screen.getByLabelText("Filter by issue code"),
      "LINE_ARITHMETIC",
    );
    expect(onChange).toHaveBeenCalledWith({
      decision: [],
      issue_code: ["LINE_ARITHMETIC"],
    });
  });
});
