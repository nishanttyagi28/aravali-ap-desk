import type { paths } from "./schema";
import type {
  DecisionOutcome,
  ErrorResponse,
  InvoiceWithDecision,
  LedgerEntry,
  Metrics,
  ReviewAction,
  ReviewQueueItem,
  ReviewResult,
} from "./types";

export type {
  DecisionOutcome,
  ErrorResponse,
  InvoiceWithDecision,
  LedgerEntry,
  Metrics,
  ReviewAction,
  ReviewQueueItem,
  ReviewResult,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly body: ErrorResponse;

  constructor(status: number, body: ErrorResponse) {
    super(body.message);
    this.status = status;
    this.body = body;
  }
}

function apiBase(): string {
  return import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";
}

async function parseError(res: Response): Promise<ErrorResponse> {
  try {
    const data = (await res.json()) as ErrorResponse;
    if (data.message) return data;
  } catch {
    /* ignore */
  }
  return {
    code: "HTTP_ERROR",
    message: res.statusText || `HTTP ${res.status}`,
    detail: null,
  };
}

async function request<T>(
  path: string,
  init?: RequestInit & { parse?: "json" | "blob" },
): Promise<T> {
  const url = `${apiBase().replace(/\/$/, "")}${path}`;
  const res = await fetch(url, init);
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  if (init?.parse === "blob") {
    return (await res.blob()) as T;
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export type ListReviewQueueParams = {
  decision?: DecisionOutcome[];
  issue_code?: string[];
};

function queryString(params: ListReviewQueueParams): string {
  const parts: string[] = [];
  for (const d of params.decision ?? []) {
    parts.push(`decision=${encodeURIComponent(d)}`);
  }
  for (const c of params.issue_code ?? []) {
    parts.push(`issue_code=${encodeURIComponent(c)}`);
  }
  return parts.length ? `?${parts.join("&")}` : "";
}

export const api = {
  listReviewQueue(params: ListReviewQueueParams = {}): Promise<ReviewQueueItem[]> {
    return request(`/review-queue${queryString(params)}`);
  },

  getInvoice(invoiceId: string): Promise<InvoiceWithDecision> {
    return request(`/invoices/${invoiceId}`);
  },

  getInvoiceFile(invoiceId: string): Promise<Blob> {
    return request(`/invoices/${invoiceId}/file`, { parse: "blob" });
  },

  reviewInvoice(invoiceId: string, body: ReviewAction): Promise<ReviewResult> {
    return request(`/invoices/${invoiceId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },

  postInvoice(invoiceId: string): Promise<LedgerEntry> {
    return request(`/invoices/${invoiceId}/post`, { method: "POST" });
  },

  getMetrics(): Promise<Metrics> {
    return request("/metrics");
  },
};

export type { paths };
