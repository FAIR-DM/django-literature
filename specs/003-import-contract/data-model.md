# Data Model: A Standard Contract for Importing Bibliographic Files

Phase 1. **No database models and no migration.** Every object here is in-memory and exists for the
duration of one import. The stored side of the feature is the existing `Item` and its related
records, reached through `from_csl_json` and not changed.

---

## The entry, and why it is not a class

One bibliographic record as it appears in a source file, before it becomes an `Item`. Three facts
travel with it through one import:

| Fact | Type | Notes |
|---|---|---|
| index | `int` | Zero-based position among the entries the format found. Assigned by `import_entries`, not the format, so no format can get the numbering wrong (FR-009) |
| handle | `str \| None` | The source's own name for this entry, where the syntax has one: a BibTeX cite key, an RIS record number. `None` when it does not (FR-009) |
| raw | `object` | Whatever the format's parser produced for this entry. Opaque to the workflow, passed back to the format's convert stage |

`raw` is deliberately untyped. It is a private handoff between a format's two stages, and typing it
would mean inventing a common intermediate that every format has to squeeze into for no benefit —
the common intermediate is CSL JSON, one stage later.

**These three are runner-local, not a public `Entry` class.** An earlier draft of this document gave
them one. Nothing constructs it: a format receives `raw` and returns CSL JSON, and what a caller
gets back is an `EntryResult` that already carries the index and the handle. A public dataclass no
caller ever builds or receives is the abstraction without a concrete use that Article III forbids,
so it was removed at US1 convergence (decision D12).

## Outcome

The fixed vocabulary an entry result draws from (FR-008). A `TextChoices` enum, so the labels are
translatable and it behaves like every other choice set in the package.

| Value | Meaning |
|---|---|
| `CREATED` | The entry became an `Item` with its related records |
| `SKIPPED` | The format recognised the element but it is not a bibliographic record, so nothing was stored and nothing is wrong |
| `FAILED` | The entry could not be stored, and `reason` says why |

Three values, every one reachable at merge. `UPDATED` and equivalents are deliberately absent —
they need matching against stored records, which decision D9 puts out of scope, and an unreachable
value is the speculation Article III forbids. Adding one later does not change the shape.

## EntryResult

The fate of a single entry. Immutable once built.

| Field | Type | Notes |
|---|---|---|
| `outcome` | `Outcome` | |
| `index` | `int` | Carried through from the entry |
| `handle` | `str \| None` | Carried through from the entry |
| `item` | `Item \| None` | The stored item, on a real run that created one. `None` for skipped, failed, **and every entry of a dry run** — see plan.md, exposing a rolled-back instance would hand back an object that looks saved and is not |
| `reason` | `str \| None` | Why it failed. Set when and only when `outcome` is `FAILED`. Translatable |

**Invariant:** `outcome is FAILED` if and only if `reason is not None`. Worth asserting in tests,
since a failure without a reason is exactly the silent drop this feature exists to remove.

## ImportResult

The report from one import run.

| Field | Type | Notes |
|---|---|---|
| `entries` | `list[EntryResult]` | One per entry the format found, in source order, each appearing once (FR-007) |
| `dry_run` | `bool` | Whether this run wrote anything (FR-016) |
| `format_name` | `str \| None` | The format's own `name` — every run sets it, since every import now starts from a `BibFormat` instance that already knows it (decision D25) |

Convenience reads over `entries`, so callers do not re-derive them and every caller counts the same
way: `created`, `skipped`, `failed` (the entry results with that outcome) and `ok` (nothing
failed).

A whole-file parse failure (FR-014) is reported as an `ImportResult` carrying a single
`EntryResult` at index 0 with outcome `FAILED` and the parser's reason. The alternative — an empty
result plus a separate error field — gives the caller two places to look for the same news, and
every caller then has to remember both.

## BibFormat

The plug-in for one file syntax, and the workflow it plugs into. An abstract base class. A subclass
must supply two stages; everything else is provided as an ordinary, overridable method (FR-003,
spec.md Refinements #2) — nothing here tries to stop a subclass reaching or replacing them, per the
maintainer's ruling that the base class only has to work when its instructions are followed.

| Member | Kind | Notes |
|---|---|---|
| `name` | class attribute, `str` | The key it is configured under, e.g. `"bibtex"` |
| `label` | class attribute, translatable `str` | Human-facing, for anything that lists the formats |
| `parse(file)` | **abstract, required** | Yields raw entries one at a time. An **iterator**, not a list — FR-024 depends on it, and a list return quietly makes the requirement unmeetable |
| `to_csl_json(raw)` | **abstract, required** | Turns one raw entry into a CSL JSON dict |
| `handle_for(raw)` | overridable, defaults to `None` | The source's own name for an entry. Optional because not every syntax has one, and requiring it would push formats into inventing identifiers |
| `import_file(file, *, dry_run=False)` | overridable, provided | The one documented entry point (FR-001). Opens the dry-run transaction and drives the rest |
| `import_entries(entries, *, dry_run)` | overridable, provided | Loops over what `parse` yielded, assigning each its index, and catches a whole-file failure raised by the iterator itself |
| `import_entry(raw, index, *, dry_run)` | overridable, provided | One entry: its handle, its conversion, its own savepoint (ADR-0006, ADR-0007) |
| `get_result(entries, *, dry_run)` | overridable, provided | Builds the `ImportResult` — the one place to reshape what a run reports without touching how any entry was imported |
| `entry_created` / `entry_skipped` / `entry_failed` | overridable, provided | Build one `EntryResult` for the matching outcome, so a subclass can change how an outcome is reported without reimplementing the loop |

Only `parse` and `to_csl_json` are abstract; a format that implements those two gets correct
behaviour from everything else. A subclass that overrides one of the provided methods takes on
whatever guarantee that method existed to provide — see ADR-0006 and ADR-0007's amendments for the
two guarantees this applies to (per-entry atomicity, and catching every exception).

## Configured formats

Not a registry. Declared under the namespaced `LITERATURE` Django setting
(`LITERATURE = {"BIB_FORMATS": ["path.to.Format", ...]}`), resolved and cached on first read, keyed
by `BibFormat.name`.

- `get_format(name)` — imports and returns the class configured under `name`, or raises
  `UnknownFormat` naming what *is* configured (FR-019).
- `available_formats()` — the configured set, so a caller can ask what exists without knowing what
  it will get back (FR-017).

Resolution fails at first read, naming the offending entry, for a path that does not import or that
resolves to something other than a usable `BibFormat` subclass (spec.md FR-017 scenario 5). The
cache is invalidated on Django's `setting_changed` signal, so `override_settings` and the `settings`
test fixture behave.

**Empty until #22.** Defaults to the formats this package ships — currently none — so the built-in
behaviour needs no configuration (Article X, FR-020). When BibTeX arrives, a host project lists its
dotted path in `LITERATURE["BIB_FORMATS"]`.
