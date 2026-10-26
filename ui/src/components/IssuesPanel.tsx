import type { ValidationIssue } from "../api/types";
import styles from "./IssuesPanel.module.css";

function isMockEvidence(evidence: ValidationIssue["evidence"]): boolean {
  if (!evidence || typeof evidence !== "object") return false;
  return Boolean((evidence as Record<string, unknown>).mock);
}

export function IssuesPanel({ issues }: { issues: ValidationIssue[] }) {
  if (!issues.length) {
    return (
      <section className={styles.panel} aria-labelledby="issues-heading">
        <h2 id="issues-heading">Validation issues</h2>
        <p className={styles.empty}>No open issues.</p>
      </section>
    );
  }

  return (
    <section className={styles.panel} aria-labelledby="issues-heading">
      <h2 id="issues-heading">Validation issues</h2>
      <ul className={styles.list}>
        {issues.map((issue, i) => (
          <li key={`${issue.code}-${i}`} className={styles.item}>
            <div className={styles.row}>
              <span className={styles.code}>{issue.code}</span>
              <span className={styles[`sev_${issue.severity}`]}>
                {issue.severity}
              </span>
              {isMockEvidence(issue.evidence) && (
                <span className={styles.mockTag}>mock</span>
              )}
            </div>
            <p className={styles.message}>{issue.message}</p>
            {issue.evidence && (
              <pre className={styles.evidence}>
                {JSON.stringify(issue.evidence, null, 2)}
              </pre>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
