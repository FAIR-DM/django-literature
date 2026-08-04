# Decisions: A Standard Contract for Importing Bibliographic Files

Rationale too long to sit inline in `spec.md`, plus every point resolved without escalation.
Maintainer decisions are marked as such. Everything else was resolved from the intake
discussion and the governing documents, and is open to veto at the spec gate.

---

## D1 — The contract lands ahead of any concrete format

**Maintainer decision.**

Article III bars a base class or indirection without a present, concrete second use, and R5 says
the contract "ships together with the first importer rather than ahead of it". Issue #21 says the
opposite: that the surface is settled "before the first format arrives". Both were written the
same day, and the contradiction was raised at intake.

Resolved in favour of the contract landing first. The reasoning that makes it consistent with
Article III rather than an exception to it: the workflow is four stages and only the first two are
format-specific. Converting CSL JSON into an `Item` is existing, exercised code with real callers
today. So the contract is not a speculative wrapper around nothing. It is a seam drawn through a
pipeline whose downstream half already exists, with two concrete formats (#22, #23) queued
immediately behind it.

An alternative was considered and rejected: routing the existing CSL JSON conversion through the
new contract as its first registered format, so that something real used it on day one. Rejected
because CSL JSON is this feature's *intermediate representation*, not one format among many.
Registering it as a format would put the pipeline's own currency on the same footing as the file
syntaxes that convert into it, which is exactly the conceptual muddle the contract exists to
prevent.

## D2 — Terminology

Self-resolved. The maintainer asked for the most appropriate terms rather than nominating any.

| Term | Meaning | Rejected alternatives |
|---|---|---|
| **format** | A plug-in for one file syntax | *provider* (says nothing about what is provided), *importer* (conflates the syntax with the act of importing) |
| **entry** | One record as it appears in a source file, before it becomes an `Item` | *record*, since `CONTEXT.md` already retires "Record" as a synonym for an item, and reusing it for the source-side unit would collide with that |
| **outcome** | The fixed vocabulary value on an entry result | *status* (suggests something that changes over time) |
| **import result** / **entry result** | The report for a run, and for one entry within it | — |

`django-import-export` was the model raised at intake, and its `BibFormat` concept maps cleanly. Its
`Resource` concept deliberately does **not** come across: a `Resource` exists so a caller can
configure how records map onto a model, and here that mapping is fixed by CSL JSON and not the
caller's to change.

## D3 — An entry is atomic

> **Graduated to [ADR-0006](../../docs/adr/0006-an-imported-entry-is-atomic.md)** at convergence. That is the standing record. This entry is kept as the working note it came from.

Self-resolved. Per-entry importing was settled at intake at the *file* level: one bad entry does
not stop the others. That leaves the level below unaddressed, because a single entry produces an
`Item` plus related `ItemName`, `ItemDate`, and `ItemIdentifier` rows, and a failure part-way
through could leave an item stripped of its contributors.

An entry is therefore all-or-nothing. Two reasons: the outcome vocabulary has no value that could
honestly describe a partial result, and Article XI treats bibliographic data as valuable and hard
to recreate, which a silently half-built item directly undermines. It is also the more useful
behaviour, because a wholly absent entry can be re-imported after the source is fixed, whereas
a partial one has to be found and repaired by hand.

## D4 — An entry is identified by index, plus a source handle where one exists

Self-resolved. The draft said "enough positional information", which is not testable.

An index is always available and is enough to locate an entry mechanically, but on its own it
serves a person badly: "entry 47 of 400 failed" gives them nothing to search for. Where the format
has a handle of its own, such as a BibTeX cite key or an RIS record number, that handle is what
its owner recognises, so it is carried too. It is optional because not every syntax has one, and requiring it
would push formats into inventing identifiers.

## D5 — The result is the reporting channel, and logging is additive

Self-resolved. Today `from_csl_json_list` skips invalid items with a `logger.warning` and returns
only the successes, which is the exact failure R5 names: a caller can tell something went wrong
only by comparing counts.

Every failure now appears in the returned result. Logging alongside it is permitted for operator
visibility but is never the sole channel. `from_csl_json_list` itself keeps its current behaviour
for callers using it directly. This feature does not change that function's contract, and
changing it would be a breaking change to a published API for no gain here.

## D6 — No throughput target

Self-resolved. R5's concern is correct handling of messy real-world files, not speed, and any
latency or throughput figure written here would be invented rather than derived from a requirement.

The one property worth constraining is memory: an import must not need a fully converted copy of
the whole file at once. Memory grows with the number of entries reported, which is unavoidable
given that the result accounts for every entry, and that growth is accepted.

## D7 — The glossary is updated in the same change

Self-resolved. The feature introduces four terms `CONTEXT.md` does not carry, and two informal
synonyms ("provider", "record") are already circulating. Article VI requires public API changes to
ship their documentation in the same PR, and `CONTEXT.md` is the file that stops vocabulary
drifting between specs. Leaving it to a follow-up is how a glossary goes stale.

## D8 — Dry run is in scope

**Maintainer decision**, taken after the feature statement was first proposed without it.

It changes the contract's shape rather than sitting on top of it, since a format must be able to
run every stage and report every outcome without anything being written. That is why it belongs in
this feature instead of being added later against a surface that did not anticipate it.

## D9 — De-duplication against stored records is out of scope

**Maintainer decision.**

Deciding when two records describe the same reference is its own problem, involving identifier
matching, disagreement between sources, and a policy on what wins. It has nothing to do with file
formats, and folding it in would make the contract carry a judgement the roadmap never asked for.

The contract still leaves room for it: because an entry's fate is one value from a fixed vocabulary
rather than a pass/fail flag, a later feature that can make that judgement reports its decisions as
*skipped* without reopening the shape settled here. Note the current behaviour this implies:
importing the same file twice today produces two copies of every entry, with citation keys
de-duplicated only within a single run.

## D10 — Detecting a file's format is out of scope

**Maintainer decision.** The caller names the format. Enumerating the registered set is in scope,
which is what lets a caller stay ignorant of the individual formats. Working out which format
a given file holds is guesswork over extensions and content, cannot be tested honestly with no real
formats registered, and is best decided wherever files are accepted from users.

## D11 — Reproducing the IntegrityError from research.md R2 needs a validation bypass

Self-resolved, during US1 implementation (T006).

research.md R2's probe demonstrated the transaction/savepoint mechanics using a raw
`ItemIdentifier.objects.create()` call that bypasses `full_clean()`. Reproducing a *real*
`IntegrityError` (rather than the `ValidationError` `full_clean()` normally raises first) through
the actual, unmodified `from_csl_json()` turns out to be structurally impossible from CSL JSON
content alone: every identifier write in that function is `full_clean()`-then-`save()`,
sequentially, and `full_clean()`'s `validate_unique()` already queries the database — so a second
identifier of a type already written for the same item is refused *before* it reaches the database,
every time. Confirmed empirically (a two-identifier probe against the real models) before writing
the test, rather than assumed.

Two things had to combine to reach the database at all, both confined to the test:

1. `DuplicateCustomIdentifier`, a `dict` subclass whose `.items()` yields the same key twice —
   something no real CSL JSON parse could ever produce (a Python `dict` cannot hold a duplicate
   key), standing in for two entries reaching `ItemIdentifier.save()` for the same `(item, type)`.
2. `bypass_identifier_validation`, a `monkeypatch`-scoped no-op for `ItemIdentifier.full_clean`,
   confined to the one test that asks for it — needed because even with (1), the *second* write's
   `full_clean()` would still catch the collision as a `ValidationError` before it reached the
   database.

Neither touches `converters.py` or any production code; both are test-only constructs, verified to
produce a genuine `sqlite3.IntegrityError` end to end through the unmodified `from_csl_json()`
before being used in `test_runner.py`. The alternative — treating research.md R2's probe as
sufficient on its own and only testing the `ValidationError` partial-failure path in T010 — was
rejected because the task explicitly asks for the `IntegrityError` path, and research.md itself
frames the two exception types as "neither can be assumed to be the only one": the runner's
`except (ValidationError, IntegrityError)` around the per-entry savepoint (`runner.py`) needs a test
that actually exercises the second branch, not only the first.

**Revisit if**: a future format-specific test needs the same trick — at that point this pairing is
worth promoting from `tests/test_importers/conftest.py` to a shared test-support module, since
duplicating the `monkeypatch` + fake-dict combination per format would be exactly the copy-paste
Article II discourages.

## D12 — The entry stays runner-local; `EntryError` is caught wherever a format raises it

**Decided at:** US1 convergence review.

Two things the US1 implementation shipped as tasks.md and plan.md asked for, both wrong on review.

**The `Entry` dataclass is removed.** T008 called for it and data-model.md described it, but nothing
in the workflow builds one — a format is handed `raw` and returns CSL JSON, and a caller gets back
an `EntryResult` that already carries the index and the handle. That leaves a public frozen
dataclass that no caller ever constructs or receives, which is the abstraction without a present
concrete use Article III bars, and exactly the kind of accumulation this feature exists to prevent.
The index, handle, and raw entry stay as three locals in the runner's loop. data-model.md is amended
to describe them as facts that travel with an entry rather than as a class.

**`EntryError` raised from `parse` no longer escapes.** exceptions.py and contracts/importers.md both
document `EntryError` as coming from `parse` as well as from `to_csl_json`, but the runner caught it
only around the convert stage, so a format that recognises a bad entry while reading the file raised
straight through `import_file` — against FR-014, which says bad file content is reported and never
raised. It is now caught alongside `ParseError`: the generator is finished either way, so the
failure is recorded against the next index and the entries already recovered are kept.

`handle_for` moved inside the same block for the same reason. It reads the same untrusted content as
`to_csl_json` (FR-023), so an entry whose handle cannot be read is now reported as a failure without
a handle rather than ending the run.

Both are covered by regression tests that were confirmed to fail against the pre-fix runner.

## D13 — `item=None` on a dry run's created entries is not the rehearsal-specific branch the brief warns against

Self-resolved, during US2 implementation (T015).

The task brief for T015 says: "There must be no rehearsal-specific branch beyond that transaction
... If you find yourself writing `if dry_run:` around conversion or storage logic, that is the
wrong design." The implementation does contain one `if dry_run` — `item=None if dry_run else item`
on the line that builds a `CREATED` `EntryResult` — which reads at first glance like exactly that.

It is not the same thing. The warning is about *execution*: a format's `to_csl_json` and
`from_csl_json` must genuinely run on a dry run rather than being skipped or faked, which is what
makes a rehearsal's outcomes observed instead of predicted. `item=None` does not skip anything —
`from_csl_json` still runs, still returns a real (in-memory) `Item`, and the local `item` variable
still holds it. The branch only decides what the *caller* is handed back afterwards, and
data-model.md and plan.md's "Design in brief" point 3 require exactly this: exposing the rolled-back
instance would hand back an object that looks saved and is not, since its rows do not survive
`set_rollback(True)`. Doing this unconditionally (never returning `item`) was rejected because it
would break FR-007's contract for a real run, where the caller does need the stored `Item`.

**Revisit if**: a future story needs the in-memory (never persisted) `Item` from a dry run for some
purpose — at that point this decision is what to reopen, not the transaction wrapping.

## D14 — The outer transaction is a `contextlib.nullcontext()` swap, not two loop bodies

Self-resolved, during US2 implementation (T015).

The two ways to make the outer `transaction.atomic()` conditional on `dry_run` are: write the loop
twice, once inside the `atomic()` block and once without, or wrap a single copy of the loop in
`transaction.atomic() if dry_run else contextlib.nullcontext()`. The first was rejected outright —
duplicating the four-stage loop is the direct opposite of "the same code path", and any later change
to the loop would need to be made twice and kept in sync by hand, which is exactly the copy-paste
Article II exists to prevent. `contextlib.nullcontext()` costs nothing at runtime and keeps
`import_file` at one loop, one set of savepoints, one place the workflow is described.

**Worth recording for whoever adds a format next (raised in this story's `concerns`, not a defect):**
research.md R5 already flags that a dry run holds one transaction open for the length of the file,
which is a long transaction on PostgreSQL for a large import. Implementing T015 confirms the
mechanism carries no additional cost beyond that already-known one — the per-entry savepoints nest
inside the outer transaction exactly as research.md R2 predicted, verified here by
`test_a_database_level_failure_inside_a_dry_run_does_not_poison_the_rest` in `test_dry_run.py`, so a
database-level failure on entry *N* of a dry run still lets entry *N+1* be reported as created. No
new interaction was found; this is a pointer back to R5 for the reader of this file, not a new
finding.

**Revisit if**: a real format's import volume makes the long-open dry-run transaction a practical
problem — the fix is a caller-side decision (chunking, a row-count cap before offering a dry run),
not a change to this mechanism.

## D15 — The dry-run guarantee is tested at the transaction level a real caller runs at

Self-resolved, during review of US2.

Every dry-run test T014 wrote runs under non-transactional `django_db`, so the test itself holds a
transaction open and the runner's outer `transaction.atomic()` is a nested savepoint. Django's
`Atomic.__exit__` handles a rollback-marked savepoint block by calling `savepoint_rollback`; at the
outermost level it instead unsets `in_atomic_block` and calls `connection.rollback()`. Those are two
different branches, and a real caller in autocommit only ever takes the second — the one nothing in
the suite covered. The mechanism does work there (verified by probe, then kept as a test), but "we
never checked" and "it works" are not the same claim, and the whole point of the feature is that a
rehearsal writes nothing.

`TestDryRunOutsideATestTransaction` covers both directions under `django_db(transaction=True)`: a
dry run leaves the row counts unchanged, and a real run commits. The first was confirmed to fail
when `transaction.set_rollback(True)` is removed.

**Revisit if**: the flush-per-test cost of `transaction=True` becomes noticeable — the answer is to
keep these two and refuse more, not to drop them.

## D16 — `import_file` sets `format_name` on a by-name run, though T018's brief did not say to

Self-resolved, during US3 implementation (T018).

`ImportResult.format_name` has existed since T004 (US1) with the docstring "the registered name
used, when the import was run by name" and the matching row in data-model.md's `ImportResult`
table, but nothing set it to anything but its `None` default, since no story before this one could
run an import by name at all. T018's task brief lists resolving a `str` through `get_format` and
letting `UnknownFormat` propagate, and does not mention this field.

Left unset, `format_name` would be a documented field that permanently reads `None` — the exact
kind of contract the data model states but the code never keeps. Since setting it is the one-line
natural completion of "run by name" (`format_name = format if isinstance(format, str) else None`,
threaded through to the `ImportResult(...)` call already being touched for `dry_run` in D14), and
the field's own docstring already commits to this behaviour, this is treated as the contract
(data-model.md) filling a gap the task brief left rather than a disagreement to escalate. Covered by
`test_result_records_the_name_used` and `test_result_format_name_is_none_when_a_class_was_passed_directly`
in `test_registry.py`.

**Revisit if**: a future story wants `format_name` to reflect the resolved class's `name` even when
a `BibFormat` subclass was passed directly (today it stays `None` in that case, matching "when the
import was run by name" read literally) — that would be a new, separate decision, not a correction
of this one.

## D17 — A format is registered only once its module has been imported, and nothing autodiscovers

Self-resolved, during review of US3 (T019).

`available_formats()` reports what has registered, and registration happens when the module
defining a format is imported. With no format in the package this is invisible, but it becomes real
at BibTeX (#22): a format decorated with `@register` in `literature/importers/formats/bibtex.py` is
absent from the registry until something imports that module, so a caller enumerating formats would
get an empty mapping and no error.

Django's answer to this is `autodiscover_modules` from `AppConfig.ready()`, which is what
`django-import-export` and the admin do. It was considered and not built: with zero formats it is
machinery over nothing (Article III), and the package's own formats need only a plain import in
`literature/importers/__init__.py` — which every caller of the contract already imports by
definition, since that is where the public surface lives (FR-021). A third-party package adding a
format registers it from its own app's `ready()`, which Django already calls.

Recorded here and in the `literature.importers` module docstring so #22 adds that import rather
than discovering the gap from an empty dropdown.

**Revisit if**: a format needs to be registered by a package that is installed but whose app is not
in `INSTALLED_APPS`, or the number of shipped formats makes an explicit import list unwieldy —
either would justify autodiscovery.

## D18 — The per-entry net catches every exception, not the three the contract names

> **Graduated to [ADR-0007](../../docs/adr/0007-the-import-runner-catches-everything.md)** at convergence. That is the standing record. This entry is kept as the working note it came from.

Self-resolved, at convergence review.

A review of the finished branch found that `import_file` could still be escaped. The runner caught
`SkipEntry`, `EntryError` and `ValidationError` around converting, and `ValidationError` and
`IntegrityError` around storing. `from_csl_json` raises neither of the latter for several shapes of
plausible CSL JSON: `{"issued": "2020"}` — a date variable as a string rather than an object —
reaches `.get()` on a string and raises `AttributeError`, and `{"author": 42}` raises `TypeError`.

Reproduced before changing anything. With three entries where the middle one carries a string date,
`import_file` raised `AttributeError`, entry one was already committed, entry three was never
attempted, and the caller received no `ImportResult` at all. That is FR-013, FR-014 and FR-023
failing together, in the exact case the contract exists for, and a format cannot prevent it: FR-003
gives it no route to the stage that fails, and `to_csl_json`'s only obligation is to return a dict.

Both `except` clauses are now `except Exception`. The cost is real and worth naming: a genuine bug
in a format, or in this package, is reported as a failed entry rather than crashing loudly. Two
things keep that honest. The reason names the exception type when it is not one the contract knows
(`KeyError: author`), so a bug does not masquerade as bad file content. And every one of them is
logged with `exc_info=True`, so the traceback is still there for whoever goes looking. This is what
`django-import-export` does for the same reason.

**Revisit if**: `from_csl_json` ever becomes strict about the shape of its input and raises
`ValidationError` for everything malformed — the narrow net would then be defensible again, though
a format with a bug would still escape it.

## D19 — `handle_for` is its own block, and an unreadable handle costs only the handle

Self-resolved, at convergence review.

The US1 review moved `handle_for` inside the block that turns a bad entry into a result, on the
grounds that it reads the same untrusted content (FR-023). That stopped it ending the run, and
introduced a worse fault: it shares the block with `to_csl_json`, so whatever `handle_for` raises is
routed as though the conversion had raised it. A `SkipEntry` out of `handle_for` reported a perfectly
good bibliographic record as "recognised, deliberately not stored" and stored it nowhere, with no
reason attached — the silent drop this whole contract exists to remove. An `EntryError` failed a
record because its *name* was unreadable.

`handle_for` now has its own `try`. Anything it raises costs the handle and nothing else: the entry
is converted, stored and reported as usual, with `handle=None` and a logged warning.

## D20 — Every transaction names the alias the models are written on

Self-resolved, at convergence review.

`transaction.atomic()` and `transaction.set_rollback(True)` both default to the `default` alias,
while `from_csl_json` writes through whichever alias `DATABASE_ROUTERS` picks for `Item`. This
package is a reusable app, so that routing is the installing project's choice. Where the two differ,
a dry run opened a transaction on an idle connection, set the rollback flag on that connection, and
let every write commit on the other one — reporting `dry_run=True` alongside a list of created
entries while permanently storing all of them. The caller had no signal at all.

Both calls, and the per-entry savepoint, now pass `using=router.db_for_write(Item)`. Covered by
`TestDryRunFollowsTheRouter`, which runs against a second database alias with a router sending
`literature` models to it. Removing either `using=` turns it red.

## D21 — Registration refuses a format that has not implemented every stage

Self-resolved, from the independent review round.

`register()` already checked that a candidate is a `BibFormat` subclass with a usable `name`, on the
stated principle that programmer error belongs at registration rather than inside somebody's import
run. It did not check that the subclass implements `parse` and `to_csl_json`. A half-written format
therefore registered cleanly and was enumerable, and the first sign of the omission was a raw
`TypeError: Can't instantiate abstract class ...` from inside `import_file` — a failure mode outside
the exception vocabulary the contract documents, raised a long way from the mistake that caused it.

`register()` now rejects any class with outstanding `__abstractmethods__`, naming the ones missing.
Covered by `test_a_format_missing_a_stage_is_refused_and_names_the_stage`, which goes red if the
check is removed.

## D22 — Two pre-existing files under `tests/` are modified, both additively

Self-resolved, at convergence. `forge tamper-check` flags any change to a test file that existed at
the base, so both are approved here in the record rather than left as unexplained flags.

`tests/settings.py` gains a second database alias. The dry-run tests route `literature` models away
from `default` through a `DATABASE_ROUTERS` setting, which is the only way to catch a transaction
opened on a different connection than the writes (D20). No existing setting changed.

`tests/test_documentation.py` adds `literature.importers` to the modules whose public symbols it
walks. The docstring gate is meant to cover the package's public surface, so a new public module has
to be in that list or the gate silently stops applying to the largest thing this feature adds.

Neither weakens an assertion. Nothing else under `tests/` that predates this branch is modified.

## D23 — Three test modules folded into the module of their subject

Self-resolved, at convergence, on a red conformance gate.

Constitution Article X requires the test tree to mirror the source tree, and `forge conformance`
enforces it: `test_dry_run.py`, `test_public_surface.py` and `test_converters_unchanged.py` each
mirrored no source module, since there is no `dry_run.py`, `public_surface.py` or
`converters_unchanged.py` to mirror. The rule's own remedy is to move a cross-cutting test into the
module of its subject as another `Test*` class.

- The dry-run tests move into `tests/test_importers/test_runner.py`. A dry run is a mode of
  `import_file`, not a second code path.
- The `from_csl_json_list` warning pin moves into `tests/test_converters.py`, whose subject it
  always was.
- The public-surface tests move into `tests/test_importers/test_smoke.py`. Their subject is the
  package `__init__`, which no test module can mirror by path, and `test_smoke.py` is the
  package-level module the rule already exempts by name.

Every test moves unchanged and the suite count is identical either side of the move. The alternative
was declaring the three under `[tool.forge.conformance] non-mirror-paths`, which the kit reserves
for tests whose subject is not a Python module at all — all three of these have one.

## D24 — `import_file` has no module-level counterpart; a caller reaches it through an instance

Self-resolved, during T026.

The maintainer's ruling said `import_file`, `import_entries`, `import_entry` and `get_result` "are
ordinary methods" and that `runner.py` is gone. That leaves open whether a convenience module-level
`import_file(file, format, dry_run=False)` should also remain, resolving `format` and delegating to
an instance. FR-001, FR-005 and FR-018 do not disambiguate on their own: "one documented way to
import," "without referring to anything specific to the file's format," and "runnable by naming a
configured format" are all satisfiable either way.

Resolved against keeping a module-level function. `runner.py` housed the whole module-scoped call,
string-vs-class resolution included; deleting the module and saying the workflow "moved onto the
class" reads as replacing that call shape, not duplicating it under the same name in two places. A
caller now writes `get_format("bibtex")().import_file(handle)` — the name passed to `get_format` is
still a string, so FR-005 and FR-018 hold, and there is exactly one documented way to run an import
(FR-001) rather than a function and a method doing the same thing under the same name at two import
paths, which is its own source of "which one is *the* entry point" confusion.

**Revisit if**: the class-then-instantiate-then-call shape proves awkward for callers in practice — a
convenience wrapper could be reintroduced later without touching `BibFormat` itself.

## D25 — `ImportResult.format_name` is always the format's own name, not sometimes `None`

Self-resolved, during T026.

D16 recorded that `format_name` stayed `None` unless an import was run by resolving a string name
through the (then) registry, because a `Format` subclass passed directly to the old module-level
`import_file` gave the runner nothing but the class itself — no name was ever looked up. That
distinction no longer exists: every import now starts from a `BibFormat` instance calling
`self.import_file(...)` on itself, and every such instance already knows its own `name`. There is no
longer a "class passed directly, so no name was resolved" case to distinguish from "name resolved
through `get_format`" — `get_format("bibtex")()` and `BibTeXFormat()` are now the same kind of value
at the point `import_file` runs, just reached two different ways.

`get_result` sets `format_name=self.name` unconditionally. `test_result_format_name_is_none_when_a_class_was_passed_directly`
(`tests/test_importers/test_registry.py`) is dropped rather than kept and weakened, because it
asserted a distinction the new call shape has no way to reproduce — there is no `import_file(file,
format_class)` call left to pass a bare class to.
`test_result_records_the_name_used` continues to cover the field, now asserting what is always true
rather than one of two cases.

**Revisit if**: a future need arises to distinguish "resolved through settings" from "held directly
by the caller" — under the current shape both are the same `instance.import_file(...)` call, so the
distinction would have to be threaded through explicitly; nothing on the instance carries it today.
