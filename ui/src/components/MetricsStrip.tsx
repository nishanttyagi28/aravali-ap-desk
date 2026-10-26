import { useEffect, useState } from "react";
import { api, ApiError, type Metrics } from "../api/client";
import { useToast } from "./Toast/ToastContext";
import styles from "./MetricsStrip.module.css";

export function MetricsStrip() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const { showError } = useToast();

  useEffect(() => {
    api
      .getMetrics()
      .then(setMetrics)
      .catch((e: unknown) => {
        if (e instanceof ApiError) showError(e.message);
      });
  }, [showError]);

  if (!metrics) return null;

  const items = [
    { label: "Processed", value: metrics.invoices_processed },
    { label: "Allow", value: metrics.allow_count },
    { label: "Review", value: metrics.review_count },
    { label: "Block", value: metrics.block_count },
    { label: "Posted", value: metrics.posted_count },
    { label: "Queue depth", value: metrics.queue_depth },
  ];

  return (
    <div className={styles.strip} aria-label="Processing metrics">
      {items.map((item) => (
        <div key={item.label} className={styles.item}>
          <span className={styles.label}>{item.label}</span>
          <span className={styles.value}>{item.value}</span>
        </div>
      ))}
    </div>
  );
}
