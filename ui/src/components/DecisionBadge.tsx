import type { DecisionOutcome } from "../api/client";
import styles from "./DecisionBadge.module.css";

const labels: Record<DecisionOutcome, string> = {
  ALLOW: "ALLOW",
  REVIEW: "REVIEW",
  BLOCK: "BLOCK",
};

export function DecisionBadge({ outcome }: { outcome: DecisionOutcome }) {
  return (
    <span className={`${styles.badge} ${styles[outcome]}`}>
      {labels[outcome]}
    </span>
  );
}
