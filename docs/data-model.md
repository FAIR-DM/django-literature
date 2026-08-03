# Data Model

The data model is a direct relational translation of the
[CSL JSON 1.0.2 specification](https://github.com/citation-style-language/schema).

## Entity overview

```
Item ──< ItemName >── Name
  │
  ├──< ItemDate
  │
  └──< ItemIdentifier
```

| Model | CSL JSON equivalent | Purpose |
|---|---|---|
| {class}`~literature.models.Item` | Top-level item object | Scalar metadata fields (title, abstract, volume, etc.) |
| {class}`~literature.models.Name` | Name-variable object | A person or organization (family, given, literal) |
| {class}`~literature.models.ItemName` | Name-variable array entry | Associates a `Name` with an `Item` for a specific CSL role, with ordering |
| {class}`~literature.models.ItemDate` | Date-variable object | A structured date or date range for a specific CSL date slot |
| {class}`~literature.models.ItemIdentifier` | Top-level string identifier fields | A typed identifier (DOI, ISBN, ISSN, URL, PMID, PMCID) |

---

## `Item` — Bibliographic entry

**Table**: `literature_item` | **CSL JSON**: top-level item object

The `Item` model stores all scalar CSL JSON fields — strings, numbers, and booleans — as
database columns. Name variables (author, editor, etc.) are stored separately in `ItemName`.
Date variables are stored in `ItemDate`. Identifiers are stored in `ItemIdentifier`.

### Key fields

| Django field | CSL JSON field | Notes |
|---|---|---|
| `citation_key` | `citation-key` | Required; application-level unique (not DB UNIQUE); used as CSL `id` on export |
| `type` | `type` | Required; one of the 45 known {class}`~literature.choices.ItemType` values |
| `title` | `title` | |
| `container_title` | `container-title` | Journal, book series, etc. |
| `publisher` | `publisher` | |
| `volume`, `issue`, `page` | `volume`, `issue`, `page` | Number-like fields stored as strings per CSL JSON spec |
| `abstract` | `abstract` | TextField |
| `categories` | `categories` | JSONField — list of category strings |
| `custom` | `custom` | JSONField — arbitrary extra fields |

All 60+ scalar CSL JSON fields are represented. See the
[full field listing](api/index.md) in the API reference.

### Citation key uniqueness

`citation_key` is **not** declared with `unique=True` in the database schema. Uniqueness is
enforced at the application level so that the same key can coexist in different library
scopes (e.g. multi-tenant deployments). The `from_csl_json()` importer automatically appends
a letter suffix (``Smith2009`` → ``Smith2009b`` → ``Smith2009c`` … → ``Smith2009z`` →
``Smith2009aa``) when a conflict is detected.

---

## `Name` — Person or organization

**Table**: `literature_name` | **CSL JSON**: name-variable object

A `Name` stores one person or organization. The same `Name` record can be linked to
many items in different roles.

| Django field | CSL JSON field | Notes |
|---|---|---|
| `family` | `family` | Family/surname |
| `given` | `given` | Given/first name |
| `literal` | `literal` | Full name as a single string (no family/given split) |
| `dropping_particle` | `dropping-particle` | e.g. "van" in Dutch names |
| `non_dropping_particle` | `non-dropping-particle` | |
| `suffix` | `suffix` | e.g. "Jr.", "III" |
| `comma_suffix` | `comma-suffix` | Place suffix after comma |
| `static_ordering` | `static-ordering` | Use western vs. eastern ordering |
| `parse_names` | `parse-names` | Instruct processor to parse name string |

:::{note}
A `Name` with only `literal` set (no `family`/`given`) represents an organization or
any contributor whose name cannot be split into structured parts. These are handled
correctly on both import and export.
:::

---

## `ItemName` — Contributor link

**Table**: `literature_itemname` | **CSL JSON**: entry in a name-variable array

`ItemName` is the ordered through-model linking `Item` to `Name`. Contributor
ordering is preserved per `(item, role)` scope: the `order` field is numbered
independently within each role on an item, so reordering authors never disturbs
editors (see ADR-0005).

| Django field | CSL JSON concept | Notes |
|---|---|---|
| `item` | — | FK → `Item` |
| `name` | — | FK → `Name` |
| `role` | name-variable key | One of 26 {class}`~literature.choices.NameRole` values (e.g. `"author"`, `"editor"`) |
| `order` | position in array | Assigned per `(item, role)` on insert (see ADR-0005) |

**Constraint**: `UNIQUE(item, role, name)` — each person can appear at most once per
role per item.

---

## `ItemDate` — Bibliographic date

**Table**: `literature_itemdate` | **CSL JSON**: date-variable object

`ItemDate` represents a single CSL date-variable slot on an item. Each item can have
at most one date per slot (enforced by `UNIQUE(item, date_type)`).

| Django field | CSL JSON field | Notes |
|---|---|---|
| `item` | — | FK → `Item` |
| `date_type` | key name (e.g. `"issued"`) | One of 6 {class}`~literature.choices.DateType` values |
| `begin` | `date-parts[0]` | Start date as `PartialDate` (year-only, year-month, or full) |
| `end` | `date-parts[1]` | End date for ranges; null for single dates |
| `season` | `season` | Seasonal qualifier (e.g. `"Spring"`) |
| `circa` | `circa` | Approximate date flag |
| `literal` | `literal` | Free-text date fallback |
| `raw_date_parts` | `date-parts` | JSONField fallback when structured parsing is not possible |

### Date precision

`begin` and `end` are `PartialDateField` values from `django-partial-date`. The
precision is preserved:

| CSL `date-parts` | Stored precision |
|---|---|
| `[[2019]]` | Year only |
| `[[2019, 8]]` | Year + month |
| `[[2019, 8, 16]]` | Full date |

---

## `ItemIdentifier` — Typed identifier

**Table**: `literature_itemidentifier` | **CSL JSON**: top-level string fields like `DOI`, `ISBN`

Each item can have at most one identifier of each type (enforced by `UNIQUE(item, type)`).

| Django field | Notes |
|---|---|
| `item` | FK → `Item` |
| `type` | Identifier type string; well-known values are {class}`~literature.choices.IdentifierType` |
| `value` | The identifier string |

**Known identifier types**: `DOI`, `ISBN`, `ISSN`, `PMID`, `PMCID`, `URL`.

All well-known types are validated at the model layer, on `save()` as well as
through `full_clean()`, so a direct `ItemIdentifier.objects.create(...)` cannot
store a malformed value:

| Type | Validation rule |
|---|---|
| `DOI` | Must match `10.\d{4,}/\S+` |
| `ISBN` | Valid ISBN-10 or ISBN-13 check digit |
| `ISSN` | Must match `\d{4}-\d{3}[\dX]` |
| `URL` | Absolute URL with `http`, `https`, or `ftp` scheme |
| `PMID` | Numeric string |
| `PMCID` | `PMC` followed by digits, or a bare digit string |

Unknown identifier types are accepted without format validation (a warning is logged).

`bulk_create()` does not call `save()`, so it bypasses these checks. That is
Django's behaviour for every model. Call `full_clean()` yourself when you build
identifiers in bulk.

---

## CSL JSON item types

All 45 CSL JSON 1.0.2 item types are enumerated in {class}`~literature.choices.ItemType`.
Four use underscores rather than hyphens as defined in the specification:
`legal_case`, `motion_picture`, `musical_score`, `personal_communication`.

## CSL JSON name roles

All 26 CSL name-variable roles are enumerated in {class}`~literature.choices.NameRole`:
`author`, `chair`, `collection-editor`, `compiler`, `composer`, `container-author`,
`contributor`, `curator`, `director`, `editor`, `editorial-director`, `executive-producer`,
`guest`, `host`, `illustrator`, `interviewer`, `narrator`, `organizer`, `original-author`,
`performer`, `producer`, `recipient`, `reviewed-author`, `script-writer`,
`series-creator`, `translator`.
