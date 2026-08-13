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
back to `id`). It is indexed but **not unique**, and nothing in the package makes it so: a key is
stored exactly as it is given, whether or not another item already carries it, and two items may
share one (ADR 0023). Keeping keys distinct is the reader's business. Do not treat it as a primary
key or as an identifier that addresses one item.

### minted citation key

A citation key a format builds from an entry's own bibliographic content, for a source syntax that
supplies no cite key of its own — RIS is the first format that needs one, since BibTeX's `ID` is
always present. Deterministic: the same entry mints the same key on every import, and the minted
key is what gets stored. An entry too sparse to mint from falls back to its
own position in the file rather than failing. Distinct from a key the source stated outright — RIS's
own `ID` tag, taken verbatim where present — which is not minted at all.

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

### format

A plug-in for one bibliographic file syntax — BibTeX, RIS — declared by dotted path in the
`LITERATURE` setting (the **configured set**, below) and reachable by name through
`literature.importers`. Implemented as a `BibFormat` subclass. A format must supply two things:
how to turn a file into entries, and how to express one entry as CSL JSON. Everything else —
looping over entries, storing one, building the report — is provided by `BibFormat` as ordinary,
overridable methods, so a format gets correct behaviour from the two required stages alone, and one
with an unusual need may replace any of the rest deliberately.

Written **format**, not *provider* or *importer*. "Provider" says nothing about what is provided,
and "importer" conflates the file syntax with the act of importing.

### configured formats

The set of formats one installation can read, declared under the namespaced `LITERATURE` setting
(`LITERATURE = {"BIB_FORMATS": ["path.to.Format", ...]}`) and enumerable through
`literature.importers.available_formats()` without knowing what is in it. Defaults to the formats
this package ships — currently none, so an empty set with no configuration required (Article X).
Not a registry: nothing is registered by a decorator or mutated at runtime, and the mapping is
resolved from settings on first read.

### entry

One bibliographic record **as it appears in a source file**, before it becomes an `Item`. The unit
an import reports against: every entry a format finds gets exactly one outcome.

`entry` and `Item` are deliberately different words for the two sides of the import boundary. An
entry is what the source file holds, and an `Item` is what the catalogue stores. An entry that is
skipped or fails never becomes an `Item` at all.

### record

RIS's own name for what this glossary calls an *entry* — opened by a `TY` (reference type) tag and
closed by `ER`, one per bibliographic item the file holds. The same relationship as *cite key*
below: two names for one thing, on either side of the import boundary, with the glossary's own term
on the catalogue side and the source format's term on the file side. Not used as a term in its own
right here — write *entry*, the way *record* is already retired as a synonym for an item (see
*Synonyms to avoid*).

### outcome

What became of one entry: **created**, **skipped**, or **failed**. A fixed vocabulary rather than a
pass/fail flag, so a later feature that can tell an entry is already in the catalogue reports that
as *skipped* without changing the shape. *Skipped* means the format recognised the element but it
is not a bibliographic record (a BibTeX `@comment`, an RIS header) — recognised and deliberately not
stored, which is not an error.

Not *status*, which suggests something that changes over time. An outcome is settled once.

### import result / entry result

The report from one import. An **import result** holds one **entry result** per entry the format
found, in source order, says whether the run was a dry run, and carries the format's own name. An
entry result carries its outcome, its index in the file, the source's own handle for it where the
syntax has one, the `Item` it produced, and — when and only when it failed — the reason.

The result is the **only** reporting channel. Logging may carry the same failures for operator
visibility, but a failure that appears solely in a log is a defect: a caller must never have to
compare a count of inputs against a count of stored items to discover something went wrong.

### dry run

An import that runs every stage and reports every outcome while leaving the catalogue exactly as it
was. Outcomes are observed rather than predicted, because the work genuinely happens inside a
transaction that is then rolled back. A dry run's entry results carry no `Item`, since those rows do
not survive the rollback.

### entry type

The kind of record a source entry declares, in the source's own vocabulary — BibTeX's `@article`,
`@book`, `@phdthesis`; RIS's `TY  - JOUR`, `TY  - BOOK`, `TY  - CHAP`. A format maps it to a CSL item
type, which is what the catalogue stores. The two vocabularies are not the same size: an entry type
with no CSL equivalent maps to the generic one rather than failing the entry.

### field

One labelled value inside a source entry, again in the source's own vocabulary — BibTeX's `journal`,
`author`, `doi`; RIS's `T2`, `AU`, `DO`. A format maps a field to a CSL variable. A field it maps to
none is preserved on the item rather than discarded, so *unmapped* describes what a format did with
a field, not something wrong with the field.

### dialect

A variant of a source format that shares its file syntax and differs in the names it uses — classic
BibTeX and BibLaTeX are one format's two dialects, one writing `journal` and `year` where the other
writes `journaltitle` and `date`. A single format reads both, because the person exporting a library
has no way to know which one their reference manager wrote. Where an entry supplies both spellings
of the same information and they disagree, precedence is documented rather than incidental.

Not every format has named dialects to point to. RIS has one written specification and no declared
variants of it, yet EndNote, Web of Science and Scopus — the producers a format reads — have each
diverged from that specification in their own undocumented ways, most visibly in which tag carries a
contributor's role. A *dialect* covers this case too: a producer's own convention for a format with
no specified variants, read by the tags it actually uses rather than by detecting which tool wrote
the file (there is no producer detection). The difference from BibTeX/BibLaTeX is only that nobody
named these conventions in advance; resolving a disagreement between them is still a precedence
question, decided the same way.

### cite key

The source's own handle for an entry, the label in `@article{shannon1948mathematical, ...}`. It is
the same value as the **citation key** above, arriving under the source's name before it becomes an
`Item`: an import reports an entry against its cite key, and the item it creates stores that value
in `Item.citation_key`. Two names for one value, on either side of the import boundary, in the same
way `entry` and `Item` are two names for the two sides of a record.

### UI app

The opt-in Django app carrying the interface, `literature.ui`. Installed alongside the core, it adds
a list page and a reference page over what the core already stores. The core has no dependency on
it, at import time or otherwise — a project can add `literature` on its own and never resolve the
UI app at all. Built on [django-mvp](https://github.com/django-mvp), which owns the interface's look
end to end; the UI app ships no styling of its own.

### catalogue

The set of stored items, spoken about from the interface. The core's own term for the same set is
the store, or `Item.objects` — *catalogue* is the UI app's word for it in prose and on the page
itself: "the catalogue list", "a catalogue holding no items".

## Synonyms to avoid

- **`Reference` / `Publication` / `Record`** for an item — the canonical term is **`Item`**
  (CSL-faithful). Renaming would introduce a deviation from CSL naming that Principle I requires be
  documented and mapped back; don't drift into these in specs.
- **`Person` / `Author`** for a contributor — use **`Name`** (may be an organization) plus a
  **role** on `ItemName`. Role is not part of the name.
- **`LiteratureItem` / `CSLDate`** — early pre-implementation names that appear in older
  constitution drafts. The implemented, canonical names are `Item` and `ItemDate`.
- **"date field"** for `ItemDate` — it is a date *slot* (one per `DateType`), not a single field.
- **`provider`** for an import plug-in — the canonical term is **format**. The word circulated
  informally while the import contract was being designed and does not appear in the code.
- **`record`** for a source-side entry — use **entry**. `Record` is already retired as a synonym
  for an item above, and reusing it on the import side would collide with that.
- **`status`** for an entry's fate — it is an **outcome**, settled once, not a state that moves.
- **`key`** on its own for a source entry's handle — write **cite key** on the source side and
  **citation key** on the model side. Both are unambiguous, and `key` is also BibTeX's name for an
  unrelated sorting field.
- **`flavour`** / **`variant`** for classic BibTeX versus BibLaTeX — the term is **dialect**.

## Notes for spec authors

- `citation_key` uniqueness is batch-scoped, not global — a spec that assumes global uniqueness is
  wrong against the current model.
- `ItemIdentifier.type` is deliberately un-validated at the choices layer; a spec that adds
  `choices=` to it would break the store-unknown-types contract (FR-017).
- One identifier per `(item, type)` and one date per `(item, date_type)` are current design limits,
  not oversights — widening either is a feature, not a fix.
- An import is per **entry**, and an entry is atomic: it lands with its names, dates and identifiers
  or it lands not at all. A spec that assumes a partly-imported entry can exist is wrong against the
  import contract.
- Importing the same file twice creates duplicates. Matching an entry against records already stored
  is deliberately out of scope, and a `citation_key` the catalogue already holds is stored again as
  given rather than resolved.
