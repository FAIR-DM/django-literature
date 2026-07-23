# ADR-0003 — Names are role-neutral and shared; role and order live on ItemName

- **Status:** Accepted (confirmed by Sam 2026-07-23)
- **Context date:** observed in `literature/models.py` (`Name`, `ItemName`), spec 001

## Context

A bibliographic entry links to contributors, each in a role (author, editor, translator, …) and a
defined order. That relationship could be modelled by storing a role on the name itself, by
duplicating a name per item, or by separating the person/organization from its role in a given item.

## Decision

`Name` is **role-neutral and shared** — it holds only the CSL name parts (`family`, `given`,
particles, `suffix`, `literal`, plus CSL flags), no role and no position, and may represent a
person *or* an organization (via `literal`). The `ItemName` through-model carries the **role**
(`NameRole`, 26 values) and the **ordered position** (`django-ordered-model`, ordered within each
`(item, role)`), unique on `(item, role, name)`.

## Consequences

- The same `Name` row is reused across items and roles — one person, many contributions.
- Querying "items by contributor X in role Y" goes through `ItemName`; role is never an attribute
  of the name.
- A contributor appears at most once per role per item; contributor order is explicit and stable.
- Institutional and unparsed names are first-class via `literal`, not a separate model.
