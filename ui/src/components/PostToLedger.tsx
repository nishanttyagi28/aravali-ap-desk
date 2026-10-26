import type { LedgerEntry } from "../api/client";
import type { DecisionOutcome } from "../api/client";
import { canPostToLedger } from "../utils/validation";
import styles from "./PostToLedger.module.css";

interface Props {
  outcome: DecisionOutcome;
  posted: boolean;
  entry: LedgerEntry | null;
  onPost: () => void;
  busy?: boolean;
}

export function PostToLedger({ outcome, posted, entry, onPost, busy }: Props) {
  const enabled = canPostToLedger(outcome, posted) && !busy;

  return (
    <section className={styles.panel} aria-labelledby="post-heading">
      <h2 id="post-heading">Ledger</h2>
      <button
        type="button"
        disabled={!enabled}
        onClick={onPost}
        aria-disabled={!enabled}
      >
        Post to ledger
      </button>
      {!enabled && outcome !== "ALLOW" && (
        <p className={styles.hint}>Posting requires ALLOW decision.</p>
      )}
      {entry && (
        <dl className={styles.meta}>
          <div>
            <dt>Seal commit</dt>
            <dd>{entry.seal.commit_id}</dd>
          </div>
          <div>
            <dt>Witness</dt>
            <dd>{entry.seal.witness_status}</dd>
          </div>
          <div>
            <dt>Posted at</dt>
            <dd>{new Date(entry.posted_at).toLocaleString()}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
