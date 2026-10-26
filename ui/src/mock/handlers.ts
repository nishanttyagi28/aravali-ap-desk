import { http, HttpResponse } from "msw";
import {
  applyPost,
  applyReview,
  getInvoiceWithDecision,
  getMetrics,
  getPosted,
  getRecord,
  listQueueItems,
} from "./store";

const base = () =>
  (import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000").replace(/\/$/, "");

function parseMulti(url: URL, name: string): string[] {
  return url.searchParams.getAll(name);
}

export const handlers = [
  http.get(`${base()}/review-queue`, ({ request }) => {
    const url = new URL(request.url);
    const items = listQueueItems({
      decision: parseMulti(url, "decision"),
      issue_code: parseMulti(url, "issue_code"),
    });
    return HttpResponse.json(items);
  }),

  http.get(`${base()}/metrics`, () => HttpResponse.json(getMetrics())),

  http.get(`${base()}/invoices/:invoiceId`, ({ params }) => {
    const id = String(params.invoiceId);
    const data = getInvoiceWithDecision(id);
    if (!data) {
      return HttpResponse.json(
        { code: "NOT_FOUND", message: "Invoice not found" },
        { status: 404 },
      );
    }
    return HttpResponse.json(data);
  }),

  http.get(`${base()}/invoices/:invoiceId/file`, async ({ params }) => {
    const id = String(params.invoiceId);
    const rec = getRecord(id);
    if (!rec) {
      return HttpResponse.json(
        { code: "NOT_FOUND", message: "Invoice not found" },
        { status: 404 },
      );
    }
    const pdfUrl = `/fixtures/${rec.invoice.source_file}`;
    const res = await fetch(pdfUrl);
    const blob = await res.arrayBuffer();
    return new HttpResponse(blob, {
      headers: { "Content-Type": "application/pdf" },
    });
  }),

  http.post(`${base()}/invoices/:invoiceId/review`, async ({ params, request }) => {
    const id = String(params.invoiceId);
    const body = (await request.json()) as {
      action: "approve" | "correct" | "reject";
      reviewer: string;
      corrections?: Record<string, unknown> | null;
    };
    const result = applyReview(id, body.action, body.corrections ?? null, body.reviewer);
    if ("error" in result) {
      if (result.error === 404) {
        return HttpResponse.json(
          { code: "NOT_FOUND", message: "Invoice not found" },
          { status: 404 },
        );
      }
      return HttpResponse.json(result.body, { status: 409 });
    }
    return HttpResponse.json(result.result);
  }),

  http.post(`${base()}/invoices/:invoiceId/post`, ({ params }) => {
    const id = String(params.invoiceId);
    const result = applyPost(id);
    if ("error" in result) {
      if (result.error === 404) {
        return HttpResponse.json(
          { code: "NOT_FOUND", message: "Invoice not found" },
          { status: 404 },
        );
      }
      return HttpResponse.json(result.body, { status: 409 });
    }
    return HttpResponse.json(result.entry);
  }),
];

export function mockLedgerFor(id: string) {
  return getPosted(id);
}
