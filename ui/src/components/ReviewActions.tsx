import styles from "./ReviewActions.module.css";

interface Props {
  onApprove: () => void;
  onReject: () => void;
  busy?: boolean;
  correctDisabled?: boolean;
}

export function ReviewActions({
  onApprove,
  onReject,
  busy,
  correctDisabled,
}: Props) {
  return (
    <div className={styles.bar} role="group" aria-label="Review actions">
      <button type="button" disabled={busy} onClick={onApprove}>
        Approve
      </button>
      <button
        type="submit"
        form="corrections-form"
        disabled={busy || correctDisabled}
      >
        Correct &amp; re-validate
      </button>
      <button type="button" className={styles.danger} disabled={busy} onClick={onReject}>
        Reject
      </button>
    </div>
  );
}
