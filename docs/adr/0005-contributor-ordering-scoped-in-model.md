# ADR-0005 — Contributor ordering is scoped per (item, role) in the model, not via django-ordered-model

- **Status:** Accepted (confirmed by Sam 2026-07-24)
- **Context date:** `literature/models.py` (`ItemName`), spec 001 (FR-003), superseded spec 002, issue #11

## Context

A contributor's position must be numbered *within its role* — the author list, the editor
list, and so on each ordered independently — so that adding or reordering an author never
shifts editor positions. Spec 001 (FR-003) specifies exactly this: ordering "scoped per
`(item, role)`".

`ItemName` was implemented with `django-ordered-model` (`OrderedModelBase`) using
`order_with_respect_to = "item"`. That scope is wrong — it numbers all contributors across the
whole item, mixing roles — but it could not be corrected within the package, because
**`order_with_respect_to` accepts ForeignKey fields only**:

- The library's system check rejects a non-FK field: `ordered_model.E005` — *"field 'role' …
  which is not a ForeignKey. This is unsupported."*
- Its runtime scope lookup (`_wrt_map`) appends `_id` to each field name (`role_id`), so a
  `CharField` would break at runtime regardless of the check.

`role` is a fixed, closed CSL 1.0.2 vocabulary (`NameRole`, 26 values), so it is a `CharField`
enum, not a ForeignKey — and making it an FK purely to satisfy the library would distort the
data model to fit a dependency. Separately, the field's `default=0` defeated the package's
auto-assignment entirely, so every row was being saved with `order = 0`.

Spec 002 (now superseded) had worked around the FK constraint by choosing the item-flat scope
and justifying it as a UI preference; that rationale rested on a false premise (that
`(item, role)` was a valid-but-worse option).

## Decision

Remove `django-ordered-model`. `ItemName` extends `django.db.models.Model`, and `order` is a
plain `PositiveIntegerField` assigned per `(item, role)` in `ItemName.save()`: a new row is
appended to the end of its own role's sequence (`max(order) + 1` within the group, starting at
0). `Meta.ordering`, the `(item, role, order)` index, and the `(item, role, name)` unique
constraint were already role-scoped and are unchanged.

## Consequences

- Contributor ordering is now correct: each role is numbered independently from zero.
- One fewer third-party dependency. The package's admin reorder widget
  (`OrderedTabularInline`) was never used, since no admin ships in the core, so nothing is lost.
- Deleting a contributor leaves a gap in its role's sequence. This is harmless: ordering is
  relative, and `order_by("order")` still yields the correct sequence. Re-packing on delete
  and interactive move up/down helpers are deferred until a front end needs them.
- Making `role` a ForeignKey to a role lookup table was rejected: CSL name-variable roles are a
  spec-fixed enumeration, not user-managed reference data.
- The change is a non-destructive `AlterField` migration (`0002_alter_itemname_order`); no
  columns are added or dropped.
