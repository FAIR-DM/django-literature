# Progress — 010 Find a reference in a large catalogue

Append-only. Each entry is written at the moment the thing it records happened.

## 2026-08-20 — intake

Grilled against issue #49, its dependency #45, the sibling issues citing R6, and the front end as
it stands after FS-009. Six questions, all answered in session. Accepted; the issue carries its
decision label.

## 2026-08-20 — specification

`spec.md` and `decisions.md` written and pushed as the bot. Five user stories, thirty-six
functional requirements, nine success criteria, ten recorded decisions. No unresolved markers.

## 2026-08-20 — setup

Issue #49 promoted to the epic in place, five story sub-issues created (#91–#95) and linked,
draft pull request #96 opened by the bot with a closing line for the epic, every story, and #88.
Title lint and the stage's exit checks green. Specification gate brief posted to the epic.

**Awaiting: specification sign-off.**

## 2026-08-20 — indexing withdrawn at the gate

The requirement to index the searched fields is dropped. An ordinary index cannot serve a
fragment search, and the alternative that can is a database-specific facility whose adoption is a
separate decision. The feature now ships no index and no migration. Specification, decisions,
requirements, success criteria, the epic and the first story updated; recorded on the issue
thread.

## 2026-08-20 — specification gate: approved

Signed off in session, with the indexing requirement withdrawn as recorded above. Planning begins.

## 2026-08-20 — planning

`research.md` (eleven findings), `plan.md` (twelve decisions) and `tasks.md` (thirty tasks across a
foundational phase and five stories) authored; ledger created and schema-valid.

The upstream surface was mapped by reading django-mvp at v0.19.1 directly. Search and filtering are
both adopted rather than written: the search mixin needs only a field list, and the filter
integration is reached by composing the documented mixin with django-filter's own view. Two findings
change the shape of the work — the filter form drops a chosen sort when it submits (raised upstream,
carried in our own form if that can be done without touching an upstream template), and no demo seed
reference carries a language, so the language filter would render empty.
