# Postmortems

Aravali AP Desk decides whether invoices are paid. When something in that path
is wrong, the useful artifact is not an apology — it is a record of what was
believed, how reality disagreed, and what now makes the same belief impossible.

These are written from the build log in
[docs/multi-agent-build.md](../docs/multi-agent-build.md), the commit history,
and the diffs. Where a cause is inferred rather than recorded, the entry says so.

## Template

```markdown
# NNNN: <the wrong thing, stated plainly>

**Severity:** high | medium | low
**Affected:** <component, version>
**Introduced:** <date>  **Found:** <date>  **Fixed:** <commit>
**Existed undetected for:** <duration>

## What we believed
The claim, as shipped.

## What was true
The gap, without softening.

## How it was found
The specific action. Not "review" — the command, the run, the recording.

## Why it survived the tests / gate
The honest reason. If the suite asserted the wrong property, say so.

## What changed
Commit, files, tests by name.

## What we did not fix
Residual exposure, so the next reader is not misled.

## What we would do differently
One or two sentences. Process changes go in GOVERNANCE.md.
```

## Index

| # | Title | Severity | Existed for |
| --- | --- | --- | --- |
| [0001](0001-token-cap-overrun.md) | A 6M token cap that could not stop a 16.1M run | medium | the whole M1–M3 build |
| [0002](0002-viewer-render-race.md) | Review UI showed upside-down pages with misaligned bbox overlays | **high** | M2-C → M6-C |
