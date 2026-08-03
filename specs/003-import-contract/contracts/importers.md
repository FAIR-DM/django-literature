# Contract: `literature.importers`

Phase 1. The public surface, signature by signature. Everything named here is importable from
`literature.importers`; nothing else in the package is public.

---

## Running an import

```python
def import_file(
    file,
    format: type[Format] | str,
    *,
    dry_run: bool = False,
) -> ImportResult
```

The one documented way to import a bibliographic file (FR-001), identical for every format
(FR-005).

- **`file`** — an open file object or anything with a `read()`. The runner does not open paths and
  does not touch the filesystem beyond what it is handed (FR-023).
- **`format`** — a `Format` subclass, or the registered name of one. A name is looked up through
  `get_format`, so an unregistered name fails with an error saying which names are registered
  (FR-019).
- **`dry_run`** — run every stage and report every outcome, then leave the catalogue exactly as it
  was (FR-015).

**Never raises for bad file content.** A file that cannot be parsed at all comes back as an
`ImportResult` whose single entry failed, with the parser's reason (FR-014). It still raises for
programmer error — an unregistered format name, or something that is not a `Format`.

**What it does, in order:**

1. Resolve the format.
2. Open an outer `transaction.atomic()` **only when `dry_run` is true**.
3. For each raw entry from `format.parse(file)`, consuming the iterator one entry at a time
   (FR-024):
   1. Assign the next index. Ask the format for a handle.
   2. Convert to CSL JSON via `format.to_csl_json`.
   3. Inside `transaction.atomic()` — a savepoint per entry — call `from_csl_json`.
   4. Record one `EntryResult`.
   Failures are caught **outside** the per-entry block, which is what lets the run continue after a
   database-level error (research.md R2). A format signalling that an element is not a
   bibliographic record yields `SKIPPED` and stores nothing.
4. On a dry run, `transaction.set_rollback(True)` before leaving the outer block.

Ordering and completeness are the runner's responsibility, not the format's: exactly one result per
entry, in the order the entries arrived (FR-007).

## Writing a format

```python
class Format(abc.ABC):
    name: ClassVar[str]
    label: ClassVar[str]          # translatable

    @abc.abstractmethod
    def parse(self, file) -> Iterator[Any]: ...

    @abc.abstractmethod
    def to_csl_json(self, raw: Any) -> dict[str, Any]: ...

    def handle_for(self, raw: Any) -> str | None:
        return None
```

Two stages to supply and one to override if the syntax has entry names of its own. A format has no
say in how an `Item` is built (FR-003) and the contract gives it no way to reach that stage.

**`parse` yields, it does not return a list.** FR-024 rests on this, and a list return makes the
requirement unmeetable from outside the format.

**Signalling that an entry is not a bibliographic record:** `to_csl_json` raises `SkipEntry`, with
an optional note. The runner records `SKIPPED` and moves on. This is how a BibTeX `@comment` or an
RIS header line is reported as "recognised, deliberately not stored" rather than as an error.

**Signalling a bad entry:** `to_csl_json` raises `EntryError` with a reason, or lets a
`ValidationError` out. Either becomes `FAILED` with the reason attached. A format never has to
build an `EntryResult` itself.

## Exceptions

| Exception | Raised by | Meaning |
|---|---|---|
| `SkipEntry` | a format, from `to_csl_json` | Recognised, not a bibliographic record. Becomes `SKIPPED` |
| `EntryError` | a format, from `parse` or `to_csl_json` | This entry is bad. Becomes `FAILED` with its reason |
| `ParseError` | a format, from `parse` | The file cannot be read at all. Becomes a one-entry failed result |
| `UnknownFormat` | `get_format` | The name is not registered. Message lists the names that are. **Reaches the caller** — it is programmer error, not file content |
| `FormatAlreadyRegistered` | `register` | That name is taken (FR-020) |

`SkipEntry`, `EntryError` and `ParseError` are the format's vocabulary for talking to the runner and
never reach the caller. `UnknownFormat` and `FormatAlreadyRegistered` are the caller's problem and
do.

## The registry

```python
def register(format_class: type[Format]) -> type[Format]     # usable as a decorator
def get_format(name: str) -> type[Format]
def available_formats() -> Mapping[str, type[Format]]
```

`register` returns the class it was given so it can sit above a class as a decorator. It raises
`FormatAlreadyRegistered` rather than replacing an existing entry (FR-020), because silently
shadowing another package's format is the kind of failure that surfaces days later as "the wrong
parser ran".

`available_formats` returns a read-only mapping. Callers enumerate; only `register` mutates.

## Reading a result

```python
result = import_file(handle, format="bibtex")

result.ok                # nothing failed
result.dry_run           # did this write anything
len(result.entries)      # one per entry in the file

for entry in result.failed:
    print(entry.index, entry.handle, entry.reason)
```

`created`, `skipped` and `failed` are filtered views over `entries`, so every caller counts the same
way rather than re-deriving it (data-model.md).

## What is not here

No format. No detection of a file's format. No export. No matching against stored records. Each is
out of scope with its reasoning in [decisions.md](../decisions.md).
