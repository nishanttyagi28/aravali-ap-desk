import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ToastProvider } from "../components/Toast/ToastContext";
import { INVOICES_CHANGED } from "../lib/invoiceEvents";
import { InvoiceDetailPage } from "./InvoiceDetailPage";

vi.mock("../components/PdfViewer", () => ({
  PdfViewer: () => null,
}));

const invoiceId = "ad689cf8-8759-f153-b778-5728f2655b19";
const base = "http://127.0.0.1:8000";

let posted = false;
let decisionOutcome = "ALLOW";

const server = setupServer(
  http.get(`${base}/invoices/:id`, () =>
    HttpResponse.json({
      invoice: {
        invoice_id: invoiceId,
        source_file: "x.pdf",
        sha256: "abc",
        page_count: 1,
        line_items: [],
        taxable_total: "1",
        cgst_total: "0",
        sgst_total: "0",
        igst_total: "0",
        grand_total: "1",
        fields: {},
        extractor_version: "t",
        mode: "offline",
      },
      decision: {
        invoice_id: invoiceId,
        outcome: decisionOutcome,
        issues: [],
        reasons: [],
        decided_by: "engine",
        decided_at: new Date().toISOString(),
      },
    }),
  ),
  http.get(`${base}/invoices/:id/file`, () =>
    HttpResponse.arrayBuffer(new ArrayBuffer(8)),
  ),
  http.get(`${base}/review-queue`, () =>
    HttpResponse.json([
      {
        invoice_id: invoiceId,
        vendor_name: "V",
        vendor_gstin: "07",
        invoice_number: "INV-1",
        invoice_date: "2025-04-01",
        grand_total: "1",
        outcome: decisionOutcome,
        top_issue_code: null,
        issue_count: 0,
        posted,
      },
    ]),
  ),
  http.post(`${base}/invoices/:id/post`, () => {
    posted = true;
    return HttpResponse.json({
      entry_id: "00000000-0000-0000-0000-000000000001",
      invoice_id: invoiceId,
      vendor_id: "V001",
      taxable_total: "1",
      cgst_total: "0",
      sgst_total: "0",
      igst_total: "0",
      cess_total: "0",
      grand_total: "1",
      posted_at: new Date().toISOString(),
      seal: {
        provider: "stub",
        commit_id: "commit-1",
        manifest_sha256: "abc",
        witness_status: "witnessed",
      },
    });
  }),
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  posted = false;
  decisionOutcome = "ALLOW";
});
afterAll(() => server.close());

vi.stubEnv("VITE_API_BASE", base);

describe("InvoiceDetail refresh", () => {
  it("refetches queue-related posted state and notifies listeners after post", async () => {
    const user = userEvent.setup();
    const events: string[] = [];
    const onChange = () => events.push("changed");
    window.addEventListener(INVOICES_CHANGED, onChange);

    render(
      <ToastProvider>
        <MemoryRouter initialEntries={[`/invoices/${invoiceId}`]}>
          <Routes>
            <Route path="/invoices/:invoiceId" element={<InvoiceDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /post to ledger/i })).toBeEnabled();
    });

    await user.click(screen.getByRole("button", { name: /post to ledger/i }));

    await waitFor(() => {
      expect(events).toContain("changed");
      expect(screen.getByText(/seal commit/i)).toBeInTheDocument();
    });

    window.removeEventListener(INVOICES_CHANGED, onChange);
  });
});
