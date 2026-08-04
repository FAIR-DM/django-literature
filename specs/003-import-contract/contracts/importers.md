# Contract: `literature.importers`

Phase 1, amended 2026-08-04 for the maintainer's Phase 7 rework (spec.md Refinements). The public
surface, signature by signature. Everything named here is importable from `literature.importers`;
nothing else in the package is public.

---

## Running an import

```python
class BibFormat(abc.ABC):
    def import_file(self, file, *, dry_run: bool = False) -> ImportResult: ...
```

The one documented way to import a bibliographic file (FR-001), identical for every format unless a
subclass deliberately overrides a step (FR-005).

- **`file`** — an open file object or anything with a `read()`. Never opened as a path — passed
  straight through to `self.parse(file)` (FR-023).
- **`dry_run`** — run every stage and report every outcome, then leave the catalogue exactly as it
  was (FR-015).

A caller reaches `import_file` through a `BibFormat` instance — either a class it already holds, or
one resolved from a name it was given:

```python
from literature.importers import get_format

with open("library.bib") as handle:
    result = get_format("bibtex")().import_file(handle)
```

`get_format` raises `UnknownFormat`, naming what *is* configured, for a name that is not (FR-019).

**Never raises for bad file content.** A file that cannot be parsed at all comes back as an
`ImportResult` whose single entry failed, with the parser's reason (FR-014).

**What the default implementation does, in order** (`import_file` → `import_entries` →
`import_entry` → `get_result`, each an ordinary method a subclass may replace):

1. Open an outer `transaction.atomic()` **only when `dry_run` is true** (`import_file`).
2. For each raw entry from `self.parse(file)`, consuming the iterator one entry at a time
   (FR-024, `import_entries`):
   1. Assign the next index. Ask the format for a handle.
   2. Convert to CSL JSON via `self.to_csl_json`.
   3. Inside `transaction.atomic()` — a savepoint per entry — call `from_csl_json` (`import_entry`).
   4. Record one `EntryResult`, via `entry_created` / `entry_skipped` / `entry_failed`.
   Failures are caught **outside** the per-entry block, which is what lets the run continue after a
   database-level error (research.md R2, ADR-0006). A format signalling that an element is not a
   bibliographic record yields `SKIPPED` and stores nothing.
3. On a dry run, `transaction.set_rollback(True)` before leaving the outer block.
4. Build the `ImportResult` (`get_result`).

Ordering and completeness are this default's responsibility, not the format's: exactly one result
per entry, in the order the entries arrived (FR-007) — true for a format that only supplies `parse`
and `to_csl_json`. A subclass replacing one of the provided steps takes over whichever of these
guarantees that step existed to keep; see ADR-0006 and ADR-0007's 2026-08-04 amendments.

## Writing a format

```python
class BibFormat(abc.ABC):
    name: ClassVar[str]
    label: ClassVar[str]          # translatable

    @abc.abstractmethod
    def parse(self, file) -> Iterator[Any]: ...

    @abc.abstractmethod
    def to_csl_json(self, raw: Any) -> dict[str, Any]: ...

    def handle_for(self, raw: Any) -> str | None:
        return None

    # Provided, ordinary methods — override any of them deliberately:
    def import_file(self, file, *, dry_run: bool = False) -> ImportResult: ...
    def import_entries(self, entries, *, dry_run: bool) -> list[EntryResult]: ...
    def import_entry(self, raw: Any, index: int, *, dry_run: bool) -> EntryResult: ...
    def get_result(self, entries: list[EntryResult], *, dry_run: bool) -> ImportResult: ...
    def entry_created(self, *, index, handle, item, dry_run) -> EntryResult: ...
    def entry_skipped(self, *, index, handle) -> EntryResult: ...
    def entry_failed(self, *, index, handle, reason) -> EntryResult: ...
```

Two stages to supply, one to override if the syntax has entry names of its own, and the rest
provided as ordinary methods a format may replace deliberately (FR-003, spec.md Refinements #2).
Nothing here tries to stop that — the maintainer's ruling was explicit: *"It's not up to us to try
and prevent novel use cases that another developer might try to invent. All we need to do is
provide a base class that will get the job done if you follow instructions. If you choose to
overwrite additional methods, all power to you."* A format that implements only `parse` and
`to_csl_json` gets correct behaviour from everything else.

**`parse` yields, it does not return a list.** FR-024 rests on this, and a list return makes the
requirement unmeetable from outside the format.

**A `parse` that reads the whole file up front still reports rather than raises.** Most third-party
bibliography parsers hand back everything at once, so a `parse` written around one raises when it is
*called* rather than when it is first iterated. The default `import_file` defers that call into
`import_entries`, so FR-014 holds for both shapes — a format author does not have to know which one
they wrote. One-at-a-time consumption (FR-024) is still only achievable by yielding.

**Signalling that an entry is not a bibliographic record:** `to_csl_json` raises `SkipEntry`, with
an optional note. The default `import_entry` records `SKIPPED` and moves on. This is how a BibTeX
`@comment` or an RIS header line is reported as "recognised, deliberately not stored" rather than as
an error.

**Signalling a bad entry:** `to_csl_json` raises `EntryError` with a reason, or lets a
`ValidationError` out. Either becomes `FAILED` with the reason attached. A format never has to
build an `EntryResult` itself unless it overrides one of the workflow methods.

## Exceptions

| Exception | Raised by | Meaning |
|---|---|---|
| `SkipEntry` | a format, from `to_csl_json` | Recognised, not a bibliographic record. Becomes `SKIPPED` |
| `EntryError` | a format, from `parse` or `to_csl_json` | This entry is bad. Becomes `FAILED` with its reason |
| `ParseError` | a format, from `parse` | The file cannot be read at all. Becomes a one-entry failed result |
| `UnknownFormat` | `get_format` | The name is not configured. Message lists the names that are. **Reaches the caller** — it is programmer error, not file content |

`SkipEntry`, `EntryError` and `ParseError` are the format's vocabulary for talking to its own
workflow methods and never reach the caller. `UnknownFormat` is the caller's problem and does.
`available_formats`/`get_format` also raise `django.core.exceptions.ImproperlyConfigured` — at
first read, not at import-run time — for a `LITERATURE["BIB_FORMATS"]` entry that does not import,
that is not a `BibFormat` subclass, or that has not implemented its two required stages.

**Anything else a format raises is reported, not raised, by the default `import_entry`.** The three
exceptions above are what a format *says*; they are not the only things that can come out of it. A
format is third-party code reading untrusted content, and the stage that builds an `Item` is not
defensive about the shape of the CSL JSON it is handed — a date variable that is a string rather
than an object raises `AttributeError` from inside `from_csl_json`, and no format can pre-empt that,
because `to_csl_json`'s only obligation is to return a dict. So the default `import_entry` reports
every exception from the converting and storing stages as a `FAILED` entry, and the default
`import_entries` reports every exception from the reading stage as a `FAILED` entry that ends the
file. The exception's type is named in the reason when it is not one the contract knows.

Nothing narrower keeps the promise at the top of this document, for a format that relies on the
default implementation. The failure it prevents is the expensive one: the exception escapes
`import_file`, so the caller gets no result for any entry, the entries after the bad one are never
attempted, and the entries already stored stay stored. A subclass overriding `import_entry` may
choose a narrower net; ADR-0007's amendment records that it then owns this promise for its own
entries.

**`handle_for` gets its own block, in the default `import_entry`.** It reads the same untrusted
content, but it only decides what an entry is *called*. An entry whose handle cannot be read is
converted and stored as normal and reported without a handle — never failed, and never given
whatever outcome the exception it raised would have meant coming from `to_csl_json`.

## Configured formats

```python
def get_format(name: str) -> type[BibFormat]
def available_formats() -> Mapping[str, type[BibFormat]]
```

Not a registry — nothing is registered by a decorator or held in mutable module state. Which
formats an installation can read is declared in Django settings, under the namespaced `LITERATURE`
key, as a list of dotted import paths (FR-017):

```python
# settings.py
LITERATURE = {
    "BIB_FORMATS": [
        "myapp.formats.BibTeXFormat",
    ],
}
```

Resolved and cached on first read; the cache is invalidated on Django's `setting_changed` signal, so
`override_settings` and the `settings` test fixture behave correctly (no test's configuration leaks
into another's). Defaults to the formats this package ships — currently none — so the built-in
behaviour needs no configuration (FR-020, Article X).

`available_formats` returns a read-only mapping. `get_format(name)` returns the class configured
under `name`, or raises `UnknownFormat` naming what *is* configured.

## Reading a result

```python
result = get_format("bibtex")().import_file(handle)

result.ok                # nothing failed
result.dry_run           # did this write anything
result.format_name       # the format's own name — always set
len(result.entries)      # one per entry in the file

for entry in result.failed:
    print(entry.index, entry.handle, entry.reason)
```

`created`, `skipped` and `failed` are filtered views over `entries`, so every caller counts the same
way rather than re-deriving it (data-model.md).

## What is not here

No format. No detection of a file's format. No export. No matching against stored records. Each is
out of scope with its reasoning in [decisions.md](../decisions.md).
