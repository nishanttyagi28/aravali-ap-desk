import type { components } from "./schema";

/** openapi-typescript embeds JSON Schema $defs on some models; strip for app use. */
type WithoutDefs<T> = Omit<T, "$defs">;

export type ErrorResponse = WithoutDefs<
  components["schemas"]["ErrorResponse.schema"]
>;
export type ReviewQueueItem = WithoutDefs<
  components["schemas"]["ReviewQueueItem.schema"]
>;
export type Metrics = WithoutDefs<components["schemas"]["Metrics.schema"]>;
export type ReviewResult = {
  decision: Decision;
  invoice: ExtractedInvoice;
};
export type ReviewAction = WithoutDefs<
  components["schemas"]["ReviewAction.schema"]
>;
export type LedgerEntry = WithoutDefs<
  components["schemas"]["LedgerEntry.schema"]
>;
export type InvoiceWithDecision = {
  invoice: WithoutDefs<components["schemas"]["ExtractedInvoice.schema"]>;
  decision: WithoutDefs<components["schemas"]["Decision.schema"]>;
};
export type Decision = components["schemas"]["Decision"];
export type ExtractedInvoice = components["schemas"]["ExtractedInvoice"];
export type ValidationIssue = components["schemas"]["ValidationIssue"];
export type DecisionOutcome = components["schemas"]["DecisionOutcome"];
export type IssueCode = components["schemas"]["IssueCode"];
