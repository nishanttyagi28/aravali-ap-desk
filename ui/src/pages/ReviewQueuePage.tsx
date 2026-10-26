import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type ReviewQueueItem } from "../api/client";
import { MetricsStrip } from "../components/MetricsStrip";
import { QueueTable, type QueueFilters } from "../components/QueueTable";
import { useToast } from "../components/Toast/ToastContext";
import { INVOICES_CHANGED } from "../lib/invoiceEvents";
import styles from "./ReviewQueuePage.module.css";

export function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<QueueFilters>({
    decision: [],
    issue_code: [],
  });
  const { showError } = useToast();

  const load = useCallback(() => {
    setLoading(true);
    api
      .listReviewQueue({
        decision: filters.decision.length ? filters.decision : undefined,
        issue_code: filters.issue_code.length ? filters.issue_code : undefined,
      })
      .then(setItems)
      .catch((e: unknown) => {
        if (e instanceof ApiError) showError(e.message);
      })
      .finally(() => setLoading(false));
  }, [filters, showError]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const onChange = () => load();
    window.addEventListener(INVOICES_CHANGED, onChange);
    return () => window.removeEventListener(INVOICES_CHANGED, onChange);
  }, [load]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Review queue</h1>
      </header>
      <MetricsStrip />
      <QueueTable
        items={items}
        filters={filters}
        onFiltersChange={setFilters}
        loading={loading}
      />
    </div>
  );
}
