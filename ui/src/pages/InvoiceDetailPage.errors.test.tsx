import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ToastProvider } from "../components/Toast/ToastContext";
import { InvoiceDetailPage } from "./InvoiceDetailPage";

vi.mock("../components/PdfViewer", () => ({
  PdfViewer: () => null,
}));

const invoiceId = "ad689cf8-8759-f153-b778-5728f2655b19";
const base = "http://127.0.0.1:8000";

const invoicePayload = {
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
    outcome: "ALLOW",
  },
  decision: {
    invoice_id: invoiceId,
    outcome: "ALLOW",
    issues: [],
    reasons: [],
    decided_by: "engine",
    decided_at: new Date().toISOString(),
  },
};

const server = setupServer(
  http.get(`${base}/invoices/:id`, () => HttpResponse.json(invoicePayload)),
  http.get(`${base}/invoices/:id/file`, () =>
    HttpResponse.arrayBuffer(new ArrayBuffer(8)),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

vi.stubEnv("VITE_API_BASE", base);

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[`/invoices/${invoiceId}`]}>
        <Routes>
          <Route path="/invoices/:invoiceId" element={<InvoiceDetailPage />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>,
  );
}

describe("InvoiceDetail API errors", () => {
  it("shows toast on 409 review and keeps decision badge ALLOW", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    });

    server.use(
      http.post(`${base}/invoices/:id/review`, () =>
        HttpResponse.json(
          { code: "CONFLICT", message: "Cannot approve" },
          { status: 409 },
        ),
      ),
    );

    await user.click(screen.getByRole("button", { name: /^approve$/i }));

    await waitFor(() => {
      expect(screen.getByText("Cannot approve")).toBeInTheDocument();
    });
    expect(screen.getByText("ALLOW")).toBeInTheDocument();
  });

  it("shows toast on 500 post without enabling ledger meta", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /post to ledger/i })).toBeEnabled();
    });

    server.use(
      http.post(`${base}/invoices/:id/post`, () =>
        HttpResponse.json(
          { code: "INTERNAL", message: "Ledger unavailable" },
          { status: 500 },
        ),
      ),
    );

    await user.click(screen.getByRole("button", { name: /post to ledger/i }));

    await waitFor(() => {
      expect(screen.getByText("Ledger unavailable")).toBeInTheDocument();
    });
    expect(screen.queryByText(/mock-seal/i)).not.toBeInTheDocument();
  });
});
