export const INVOICES_CHANGED = "ap-desk-invoices-changed";

export function notifyInvoicesChanged(): void {
  window.dispatchEvent(new Event(INVOICES_CHANGED));
}
