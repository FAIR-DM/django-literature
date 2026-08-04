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
| index | `int` | Zero-based position among the entries the format found. Assigned by the runner, not the format, so no format can get the numbering wrong (FR-009) |
| handle | `str \| None` | The source's own name for this entry, where the syntax has one: a BibTeX cite key, an RIS record number. `None` when it does not (FR-009) |
| raw | `object` | Whatever the format's parser produced for this entry. Opaque to the runner, passed back to the format's convert stage |

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
| `format_name` | `str \| None` | The registered name used, when the import was run by name |

Convenience reads over `entries`, so callers do not re-derive them and every caller counts the same
way: `created`, `skipped`, `failed` (the entry results with that outcome) and `ok` (nothing
failed).

A whole-file parse failure (FR-014) is reported as an `ImportResult` carrying a single
`EntryResult` at index 0 with outcome `FAILED` and the parser's reason. The alternative — an empty
result plus a separate error field — gives the caller two places to look for the same news, and
every caller then has to remember both.

## BibFormat

The plug-in for one file syntax. An abstract base class, with two stages a subclass must supply.

| Member | Kind | Notes |
|---|---|---|
| `name` | class attribute, `str` | The registry key, e.g. `"bibtex"` |
| `label` | class attribute, translatable `str` | Human-facing, for anything that lists the formats |
| `parse(file)` | abstract | Yields raw entries one at a time. An **iterator**, not a list — FR-024 depends on it, and a list return quietly makes the requirement unmeetable |
| `to_csl_json(raw)` | abstract | Turns one raw entry into a CSL JSON dict |
| `handle_for(raw)` | overridable, defaults to `None` | The source's own name for an entry. Optional because not every syntax has one, and requiring it would push formats into inventing identifiers |

A format has no other members. It cannot touch how an `Item` is built (FR-003), and nothing in the
contract offers it a way to.

## The registry

Module-level, keyed by `BibFormat.name`. Not a model, not a setting — an in-process mapping populated
by explicit registration.

- `register(format_class)` — adds it. Raises on a name already registered, rather than replacing it
  in silence (FR-020).
- `get_format(name)` — returns the class, or raises an error naming what *is* registered (FR-019).
- `available_formats()` — the registered set, so a caller can ask what exists without knowing what
  it will get back (FR-017).

**Empty until #22.** Autodiscovery through the app registry's `ready()` hook was considered and
rejected: with no formats to discover it is machinery serving nothing, which Article II rules out.
When BibTeX arrives it registers itself on import, and if a third format ever comes from outside
the package, that is when autodiscovery earns its place.
