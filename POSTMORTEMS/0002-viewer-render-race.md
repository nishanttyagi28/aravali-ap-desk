# 0002: Review UI showed upside-down pages with misaligned bbox overlays

**Severity:** high — this is the review step, and the review step is the last line of defence
**Affected:** `ui/` review UI, M2-C → M6
**Introduced:** M2-C (`bd64b9b`, 2026-10-26 21:22)  **Found:** during review-UI use, 2026-10-27
**Fixed:** `2f7bbbe` (2026-10-27 22:27)  **Existed undetected for:** ~25 hours and one demo recording

## What we believed

Bounding boxes were correct. `AGENTS.md` pins the convention precisely — *PDF
user space of the unrotated page, points, origin bottom-left, y increases
upward* — and `ui/src/utils/bbox.ts` had tests for the conversion. The UI drew
each box from the stored coordinates with that conversion.

On that reading, provenance display was solved: the extractor records page and
bbox, the UI draws it, a human sees exactly where the field came from.

## What was true

Pages could render **upside down**, and the boxes landed in the **wrong place**
on the page.

The cause was not the coordinate math. It was a render race: `pdf.js`
`RenderTask`s that had been superseded were never cancelled or awaited, so a
stale render could paint into the buffer after a newer one, and the overlay was
positioned from a viewport that did not match the page actually on screen.

The bbox transform was correct; the pixels it was drawn over were not the pixels
it described.

## Why this matters more than a cosmetic bug

A REVIEW or BLOCK invoice is the case where a human is asked to look at the
document and decide. If the overlay is offset, the reviewer approves or blocks
while looking at the **wrong region of the page** — and does so with the
confidence that comes from a highlight box.

The failure mode is not "the UI looked odd". It is **a human sign-off on
evidence they did not actually see.** Every other control in this repo — the
frozen contracts, the fail-closed hooks, the gate, the approval trailers — exists
to make that sign-off meaningful. This bug attacked the one step that cannot be
delegated.

## How it was found

In manual use of the Review UI. The first demo recording
(`docs/demo/aravali-demo.mp4`, commit `59e2d67`) captured it: the BLOCK invoice
detail showed the page inverted with the overlay misplaced.

The fix was then approved explicitly by the owner — the only commit in the build
with an owner sign-off rather than the standing auto-approval
(`Supervisor-Approval: ... M6 (viewer bug fix) approved by owner 2026-10-27 9:49 PM IST`).
The demo was re-recorded afterwards (`6ec2c4f`: *"re-record demo video v2 ... BLOCK
invoice detail upright after M6 viewer fix"*).

## Why it survived the tests and the gate

Because the tests asserted the property that was already correct.

`bbox.ts` and `bbox.test.ts` test a **pure function**: given a bbox and a page
height, return corners. That function worked. Nothing tested the **async render
lifecycle** — which render task owns the buffer, which viewport the overlay was
measured against, what happens when a second render starts before the first
finishes.

Evidence from the fix diff, and this part is inference from the diff rather than
a recorded statement:

- `ui/src/utils/bbox.ts` — **+9 lines**. The coordinate math barely changed.
- `ui/src/components/PdfViewer.tsx` — **+109 lines**. The lifecycle changed a lot.
- `ui/src/components/PdfViewer.test.tsx` — **+363 lines**. Where the missing
  tests went.

The bug lived exactly where there were no tests, in the shape that pure-function
tests cannot reach.

## What changed

`2f7bbbe` — *"fix PDF viewer render race (upside-down page / misplaced bboxes):
cancel superseded RenderTasks, render-id guard, offscreen buffer, overlay state
from displayed viewport; regression tests"*

- `tearDownRenderResources()` — cancels the active `RenderTask`, awaits its
  promise to absorb `RenderingCancelledException`, then destroys the
  `PDFDocumentProxy` and the `PDFDocumentLoadingTask`.
- A render-id guard so a stale render cannot write after a newer one starts.
- An offscreen buffer, so a partially-painted page is never displayed.
- Overlay state derived from the **displayed** viewport rather than the requested
  one.
- `normalizePageRotation()` in `bbox.ts`, so rotation is handled at the boundary.
- 363 lines of tests in `PdfViewer.test.tsx`; `bbox.test.ts` updated.

## What we did not fix

- **The extractor is not part of this fix.** `docai/extract` is covered by the
  same coordinate convention, and the UI now normalises rotation — but a
  non-rotated render path is not proof that every producer emits boxes the same
  way. `AGENTS.md` warns that top-left producers must convert; nothing verifies
  a given producer did.
- **No visual regression test.** The new tests assert lifecycle and geometry,
  not "the highlighted region and the text it highlights are the same region on
  a rotated page". That assertion is what would actually have caught this.
- **The demo video is the regression test.** For two of these incidents the
  detector was a human watching a recording. That is not a control.

## What we would do differently

When the UI's job is to *show evidence*, the test must compare what the human
sees against what was claimed — not just that the coordinate helper returns the
right numbers. The property to assert is "the box is over the invoice number",
and it is checkable, and it was not checked for 25 hours while a demo recording
was made and shipped.

Recorded in `GOVERNANCE.md`: lanes constrain paths, not quality, and a green gate
only proves what someone thought to assert.
