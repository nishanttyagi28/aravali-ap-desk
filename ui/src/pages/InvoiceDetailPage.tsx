import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  ApiError,
  type InvoiceWithDecision,
  type LedgerEntry,
} from "../api/client";
import { CorrectionForm } from "../components/CorrectionForm";
import { DecisionBadge } from "../components/DecisionBadge";
import { IssuesPanel } from "../components/IssuesPanel";
import type { OverlayField } from "../components/BboxOverlay";
import { PdfViewer } from "../components/PdfViewer";
import { PostToLedger } from "../components/PostToLedger";
import { ReviewActions } from "../components/ReviewActions";
import { useToast } from "../components/Toast/ToastContext";
import { notifyInvoicesChanged } from "../lib/invoiceEvents";
import { listExtractedFields } from "../utils/fields";
import styles from "./InvoiceDetailPage.module.css";

const REVIEWER = "ui-reviewer";

export function InvoiceDetailPage() {
  const { invoiceId } = useParams<{ invoiceId: string }>();
  const [data, setData] = useState<InvoiceWithDecision | null>(null);
  const [pdf, setPdf] = useState<Blob | null>(null);
  const [ledger, setLedger] = useState<LedgerEntry | null>(null);
  const [posted, setPosted] = useState(false);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [busy, setBusy] = useState(false);
  const { showError, showSuccess } = useToast();

  const load = useCallback(async () => {
    if (!invoiceId) return;
    try {
      const d = await api.getInvoice(invoiceId);
      setData(d);
      const queue = await api.listReviewQueue();
      const row = queue.find((q) => q.invoice_id === invoiceId);
      if (row?.posted) {
        setPosted(true);
      }
    } catch (e: unknown) {
      if (e instanceof ApiError) showError(e.message);
    }
    try {
      const blob = await api.getInvoiceFile(invoiceId);
      setPdf(blob);
    } catch (e: unknown) {
      if (e instanceof ApiError) showError(e.message);
    }
  }, [invoiceId, showError]);

  useEffect(() => {
    load();
  }, [load]);

  const overlayFields: OverlayField[] = useMemo(() => {
    if (!data) return [];
    return listExtractedFields(data.invoice).map(({ name, field }) => ({
      name,
      bbox: field.bbox!,
      confidence: field.confidence,
    }));
  }, [data]);

  const applyResult = (result: InvoiceWithDecision) => {
    setData(result);
  };

  const runReview = async (
    action: "approve" | "correct" | "reject",
    corrections?: Record<string, string>,
  ) => {
    if (!invoiceId) return;
    setBusy(true);
    try {
      const result = await api.reviewInvoice(invoiceId, {
        action,
        reviewer: REVIEWER,
        corrections: corrections ?? null,
      });
      applyResult(result as InvoiceWithDecision);
      notifyInvoicesChanged();
      await load();
      showSuccess(`Review action "${action}" applied`);
    } catch (e) {
      if (e instanceof ApiError) showError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const onPost = async () => {
    if (!invoiceId) return;
    setBusy(true);
    try {
      const entry = await api.postInvoice(invoiceId);
      setLedger(entry);
      setPosted(true);
      notifyInvoicesChanged();
      await load();
      showSuccess("Posted to ledger");
    } catch (e) {
      if (e instanceof ApiError) showError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (!invoiceId) {
    return <p>Missing invoice id</p>;
  }

  if (!data) {
    return <p className={styles.loading}>Loading invoice…</p>;
  }

  const { invoice, decision } = data;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link to="/">← Queue</Link>
        <h1>{invoice.invoice_number ?? invoice.invoice_id}</h1>
        <DecisionBadge outcome={decision.outcome} />
      </header>

      <div className={styles.layout}>
        <div className={styles.pdfCol}>
          <PdfViewer
            file={pdf}
            pageNumber={pageNumber}
            pageCount={invoice.page_count ?? 1}
            onPageChange={setPageNumber}
            fields={overlayFields}
            highlighted={highlighted}
            onHighlight={setHighlighted}
          />
        </div>
        <div className={styles.sideCol}>
          <IssuesPanel issues={decision.issues} />
          <CorrectionForm
            invoice={invoice}
            highlighted={highlighted}
            onHighlight={setHighlighted}
            onSubmitCorrections={(c) => runReview("correct", c)}
            disabled={busy}
          />
          <ReviewActions
            busy={busy}
            onApprove={() => runReview("approve")}
            onReject={() => runReview("reject")}
          />
          <PostToLedger
            outcome={decision.outcome}
            posted={posted}
            entry={ledger}
            onPost={onPost}
            busy={busy}
          />
        </div>
      </div>
    </div>
  );
}
