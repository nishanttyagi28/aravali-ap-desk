import type {
  Decision,
  DecisionOutcome,
  ExtractedInvoice,
  IssueCode,
  LedgerEntry,
  ReviewQueueItem,
  ValidationIssue,
} from "../api/types";
import mockData from "./data.json";

interface MockInvoiceRecord {
  invoice_id: string;
  expected_decision: string;
  expected_issue_codes: string[];
  invoice: ExtractedInvoice;
  vendor_name: string | null;
  vendor_id: string;
}

const records = (mockData as { invoices: MockInvoiceRecord[] }).invoices;

const posted = new Map<string, LedgerEntry>();
const overrides = new Map<string, { decision: Decision; invoice: ExtractedInvoice }>();

function mockIssue(code: IssueCode, index: number): ValidationIssue {
  const severity: ValidationIssue["severity"] =
    code === "LOW_CONFIDENCE" ? "warn" : "error";
  return {
    code,
    severity,
    message: `[mock] Synthetic validation message for ${code}`,
    field: null,
    evidence: { mock: true, placeholder: true, index },
  };
}

function buildDecision(rec: MockInvoiceRecord): Decision {
  const override = overrides.get(rec.invoice_id);
  if (override) return override.decision;

  const now = new Date().toISOString();
  const issues = rec.expected_issue_codes.map((code, i) =>
    mockIssue(code as IssueCode, i),
  );
  return {
    invoice_id: rec.invoice_id,
    outcome: rec.expected_decision as DecisionOutcome,
    issues,
    reasons: issues.map((i) => i.message),
    decided_by: "engine",
    decided_at: now,
  };
}

function getInvoice(rec: MockInvoiceRecord): ExtractedInvoice {
  const override = overrides.get(rec.invoice_id);
  return override?.invoice ?? rec.invoice;
}

export function getRecord(id: string): MockInvoiceRecord | undefined {
  return records.find((r) => r.invoice_id === id);
}

export function listQueueItems(filters: {
  decision?: string[];
  issue_code?: string[];
}): ReviewQueueItem[] {
  let items = records.map((rec) => {
    const decision = buildDecision(rec);
    const inv = getInvoice(rec);
    const top = decision.issues[0]?.code ?? null;
    return {
      invoice_id: rec.invoice_id,
      vendor_name: rec.vendor_name,
      vendor_gstin: inv.vendor_gstin,
      invoice_number: inv.invoice_number,
      invoice_date: inv.invoice_date,
      grand_total: inv.grand_total,
      outcome: decision.outcome,
      issue_count: decision.issues.length,
      top_issue_code: top,
      posted: posted.has(rec.invoice_id),
    } as ReviewQueueItem;
  });

  if (filters.decision?.length) {
    const set = new Set(filters.decision);
    items = items.filter((i) => set.has(i.outcome));
  }
  if (filters.issue_code?.length) {
    const set = new Set(filters.issue_code);
    items = items.filter((i) => i.top_issue_code && set.has(i.top_issue_code));
  }
  return items;
}

export function getInvoiceWithDecision(id: string) {
  const rec = getRecord(id);
  if (!rec) return null;
  return {
    invoice: getInvoice(rec),
    decision: buildDecision(rec),
  };
}

export function applyReview(
  id: string,
  action: "approve" | "correct" | "reject",
  corrections: Record<string, unknown> | null,
  reviewer: string,
) {
  const rec = getRecord(id);
  if (!rec) return { error: 404 as const };

  const inv = { ...getInvoice(rec) };
  if (action === "correct" && corrections) {
    Object.assign(inv, corrections);
  }

  const now = new Date().toISOString();
  let outcome: Decision["outcome"];
  let issues = buildDecision(rec).issues;

  if (action === "reject") {
    outcome = "BLOCK";
    issues = [
      mockIssue("MISSING_FIELD", 0),
      {
        code: "MISSING_FIELD",
        severity: "error",
        message: `[mock] Rejected by reviewer ${reviewer}`,
        field: null,
        evidence: { mock: true, rejected: true },
      },
    ];
  } else if (action === "approve") {
    if (rec.expected_decision === "BLOCK" && !corrections) {
      return {
        error: 409 as const,
        body: {
          code: "CONFLICT",
          message: "Cannot approve while blocking issues remain",
        },
      };
    }
    outcome = "ALLOW";
    issues = [];
  } else {
    outcome = rec.expected_decision as Decision["outcome"];
    if (action === "correct") {
      outcome = rec.expected_issue_codes.length === 0 ? "ALLOW" : "REVIEW";
      issues =
        outcome === "ALLOW"
          ? []
          : rec.expected_issue_codes.map((code, i) => mockIssue(code as IssueCode, i));
    }
  }

  const decision: Decision = {
    invoice_id: id,
    outcome,
    issues,
    reasons: issues.length ? issues.map((i) => i.message) : ["[mock] Approved"],
    decided_by: "human",
    decided_at: now,
  };
  overrides.set(id, { decision, invoice: inv });
  return { result: { decision, invoice: inv } };
}

export function applyPost(id: string) {
  const rec = getRecord(id);
  if (!rec) return { error: 404 as const };
  const decision = buildDecision(rec);
  if (decision.outcome !== "ALLOW") {
    return {
      error: 409 as const,
      body: { code: "NOT_POSTABLE", message: "Invoice is not ALLOW" },
    };
  }
  if (posted.has(id)) {
    return {
      error: 409 as const,
      body: { code: "ALREADY_POSTED", message: "Already posted to ledger" },
    };
  }
  const inv = getInvoice(rec);
  const entry: LedgerEntry = {
    entry_id: crypto.randomUUID(),
    invoice_id: id,
    vendor_id: rec.vendor_id,
    taxable_total: inv.taxable_total,
    cgst_total: inv.cgst_total,
    sgst_total: inv.sgst_total,
    igst_total: inv.igst_total,
    cess_total: inv.cess_total ?? "0",
    grand_total: inv.grand_total,
    posted_at: new Date().toISOString(),
    seal: {
      provider: "stub",
      commit_id: `mock-seal-${id.slice(0, 8)}`,
      manifest_sha256: inv.sha256,
      witness_status: "witnessed",
    },
  };
  posted.set(id, entry);
  return { entry };
}

export function getMetrics() {
  const items = listQueueItems({});
  const allow = items.filter((i) => i.outcome === "ALLOW").length;
  const review = items.filter((i) => i.outcome === "REVIEW").length;
  const block = items.filter((i) => i.outcome === "BLOCK").length;
  const postedCount = items.filter((i) => i.posted).length;
  return {
    invoices_processed: items.length,
    allow_count: allow,
    review_count: review,
    block_count: block,
    posted_count: postedCount,
    queue_depth: review + block,
  };
}

export function getPosted(id: string): LedgerEntry | undefined {
  return posted.get(id);
}
