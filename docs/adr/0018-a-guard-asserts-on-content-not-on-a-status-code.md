# ADR-0018 — A guard asserts on content, not on a status code

- **Status:** Accepted
- **Context date:** spec 007 (D3), `demo/smoke.py`, issue #46

## Context

The demo project doubles as a regression guard: a check starts it through its own wiring on every
change and confirms its pages still render. What "still render" means turns out to decide whether
the guard is worth having.

The catalogue list is required to render an empty-state page when it finds nothing, which
ADR-0016's front end settled and the browse feature delivered. So a demo whose seed never loaded
serves a well-formed page and returns 200. A reference page whose record has no contributors, no
dates and no identifiers does the same. Every failure this guard exists to catch produces a
healthy response code.

## Decision

**A guard asserts on what the page contains, never on the code it returned.** Each page in the
walk must respond successfully *and* carry content that could only have come from the seeded
catalogue. A step that can be satisfied by an empty page is not a check.

This binds the walk that exists today and every extension of it. Creating and editing references,
managing contributors, search and import each add pages to the demo, and each adds its assertions
in this form.

## Consequences

Writing a step costs more than a status assertion, because the author has to name something the
page can only show when the system underneath it worked. That is the work, not an overhead on it.

The guard is falsifiable, which a status check is not. Removing the seeding step from the start
command turns it red while the full test suite stays green — the drift class the guard was added
for, demonstrated rather than asserted.

A step can fail for a reason unrelated to its subject, because content depends on more of the
system than a response code does. Failures therefore report the address, the status and a bounded
excerpt of the body, so the reader can tell a broken page from a broken expectation without
running the demo by hand.

## Alternatives considered

**Assert on status codes and check content only on the catalogue list.** Cheaper, and it catches a
crash. It does not catch an unseeded demo, a page rendering an empty record, or a redirect to a
login — the failures that reach a reader as "the demo is broken" while CI stays green.

**Compare rendered pages against stored snapshots.** Stronger on paper. In practice it fails on
every deliberate change to the front end, and a check that cries wolf on ordinary work gets
disarmed.
