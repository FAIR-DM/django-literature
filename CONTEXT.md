# django-literature — Domain Model

<!-- Ubiquitous language for this repo. Drafted at onboarding from the source code (the
     authoritative reference), cross-checked against the README. This pins the vocabulary that
     specs, plans, and reviews must use. -->

The package is a relational representation of the [CSL JSON 1.0.2](https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html)
bibliographic interchange format. One rule drives the design: when CSL JSON names a concept, this
package mirrors that name rather than inventing its own. The glossary uses those CSL names on
purpose.

## Glossary

### Item

The top-level bibliographic entry — one book, article, dataset, map, and so on. Persisted as the
`Item` model, which stores every scalar CSL field (titles, publisher, volume, page, …) as its own
column; name-, date-, and identifier-variables live in the related models below. An item's kind is
one of 45 `ItemType` values (`article-journal`, `book`, `chapter`, …).

`Item` is deliberately the CSL term, not `Reference`/`Publication`/`Record` (see *Synonyms to
avoid*). It is generic at an import site, but the `literature` app namespace carries the meaning
(`literature.Item`), and faithfulness to CSL is the point of the package.

### citation key

The human-facing handle for an item (`Item.citation_key`), mapping to CSL `citation-key` (falling
back to `id`). It is indexed but **not globally unique** — uniqueness is resolved *per import
batch*: `from_csl_json` de-duplicates colliding keys by appending a suffix. Do not treat it as a
primary key or a cross-batch stable identifier.

### Name

A contributor — a person **or** an organization — stored role-neutrally as the `Name` model
(`family`, `given`, particles, `suffix`, `literal`, plus CSL flags like `static_ordering`).
Institutional or unparsed names use `literal`. A `Name` carries no role and no position on its own;
those belong to `ItemName`. Names are shared across items.

Not `Person` or `Author`: a `Name` may be an organization, and its role (author, editor, …) is a
property of the link, not the name.

### ItemName

The ordered through-model binding a `Name` to an `Item` in a specific **role** and **position**.
Role is one of 26 `NameRole` values (`author`, `editor`, `translator`, …); order is preserved
per `(item, role)` scope, numbered independently within each role and assigned in the model's
`save()` (see ADR-0005). Unique on `(item, role, name)` — the same contributor appears at most
once per role per item.

### ItemDate

A structured date occupying one CSL **date slot** on an item (`DateType`, 6 slots: `accessed`,
`available-date`, `event-date`, `issued`, `original-date`, `submitted`). At most one `ItemDate`
per `(item, date_type)`. Dates are partial by nature — `begin`/`end` are `PartialDateField`s
supporting year-only, year-month, or full-date precision; a range sets both (`end` never without
`begin`). Un-normalizable source dates fall back to `literal`, `raw`, or `raw_date_parts`.

### ItemIdentifier

A typed `(type, value)` identifier attached to an item (DOI, ISBN, ISSN, PMID, PMCID, URL, or any
other string). The `type` field intentionally has **no `choices=` validation** so unknown
identifier types are stored rather than rejected; `IdentifierType` enumerates the 6 known types for
lookup and documentation only. Known-type formats are format-validated (see *Identifier
validation*). Unique on `(item, type)` — one identifier per type per item (multiple ISBNs are out
of scope).

### CSL JSON

The Citation Style Language JSON 1.0.2 specification — the canonical interchange format and the
authoritative reference for item types, name/date variables, and identifiers. Written **CSL JSON**
throughout (not "CSL-JSON" in prose, though the constitution and some docstrings use the hyphen).

### Conversion / round-trip fidelity

The import/export boundary: `from_csl_json` / `from_csl_json_list` build model instances from CSL
JSON dicts, and `to_csl_json` renders an item back to a standards-compliant dict. The governing
guarantee is **round-trip fidelity** — importing then exporting yields equivalent CSL JSON.

### Identifier validation

Model-layer format validators (`validators.py`) for the known identifier types: `validate_doi`,
`validate_isbn` (ISBN-10/13 checksum), `validate_issn`, `validate_url`, `validate_pmid`,
`validate_pmcid`. Invalid known-type identifiers are rejected at the model/form layer, never
silently stored; unknown types bypass validation by design.

## Synonyms to avoid

- **`Reference` / `Publication` / `Record`** for an item — the canonical term is **`Item`**
  (CSL-faithful). Renaming would introduce a deviation from CSL naming that Principle I requires be
  documented and mapped back; don't drift into these in specs.
- **`Person` / `Author`** for a contributor — use **`Name`** (may be an organization) plus a
  **role** on `ItemName`. Role is not part of the name.
- **`LiteratureItem` / `CSLDate`** — early pre-implementation names that appear in older
  constitution drafts. The implemented, canonical names are `Item` and `ItemDate`.
- **"date field"** for `ItemDate` — it is a date *slot* (one per `DateType`), not a single field.

## Notes for spec authors

- `citation_key` uniqueness is batch-scoped, not global — a spec that assumes global uniqueness is
  wrong against the current model.
- `ItemIdentifier.type` is deliberately un-validated at the choices layer; a spec that adds
  `choices=` to it would break the store-unknown-types contract (FR-017).
- One identifier per `(item, type)` and one date per `(item, date_type)` are current design limits,
  not oversights — widening either is a feature, not a fix.
