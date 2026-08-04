# ADR-0007 — `import_entry` catches every exception by default, not a named few

- **Status:** Accepted, amended 2026-08-04 for the maintainer's Phase 7 rework
- **Context date:** spec 003 (FR-013, FR-014, FR-023), `literature/importers/base.py`, issue #21

## Context

The import contract promises that bad file content is reported through the returned result rather
than raised at the caller (FR-014), that every failure appears in that result (FR-013), and that no
file content, however malformed, causes an unhandled error (FR-023).

The first implementation caught the exceptions the contract names: `SkipEntry`, `EntryError` and
`ValidationError` around converting an entry, and `ValidationError` and `IntegrityError` around
storing it. That reads like the careful choice — catch what you understand, let genuine bugs
surface.

Reviewing the finished branch showed it does not hold. `from_csl_json` raises neither of those for
several shapes of plausible CSL JSON:

- `{"issued": "2020"}` — a date variable given as a string rather than an object — reaches `.get()`
  on a string and raises `AttributeError`.
- `{"author": 42}` raises `TypeError`.

Both are things a real file can contain and a reasonable format can hand over. Reproduced before
anything was changed: three entries, the middle one carrying a string date. `import_file` raised
`AttributeError`, entry one was already committed, entry three was never attempted, and the caller
got no `ImportResult` at all. Three requirements failed together, in exactly the case the contract
exists for.

A format cannot defend against this. Article III of this spec gives it no route to the stage that
fails, and its only obligation is to return a dict.

## Decision

Both `except` clauses, in `BibFormat.import_entry`, catch `Exception`. Any exception raised while
converting or storing one entry becomes that entry's failure, and the run continues.

Two things keep this from hiding real bugs:

- When the exception is not one the contract knows about, its type is named in the reason
  (`KeyError: author`), so a defect in a format or in this package does not masquerade as bad file
  content.
- Every caught exception is logged with `exc_info=True`, so the traceback is available to whoever
  goes looking.

This is what `django-import-export` does at its row boundary, for the same reason.

**Amendment, 2026-08-04.** `import_entry` is no longer a step inside a module-level function a
format has no way to reach — it is an ordinary method on `BibFormat`, and the maintainer's ruling
was explicit that nothing should try to stop a subclass from overriding it. What follows was
written as an unconditional guarantee of the whole contract; it is now what `import_entry` does
**by default**, and a subclass that overrides it inherits the responsibility of keeping the
guarantee, not the guarantee itself.

## Consequences

- **By default**, the contract's promise holds for any input, rather than for the subset of
  malformed input whose failure mode was anticipated — this is true for every format that does not
  override `import_entry`, which is the base class's whole job.
- **A genuine bug in a format, or in this package, is reported as a failed entry rather than
  crashing loudly**, under the default `import_entry`. That is the real cost and it is accepted
  knowingly: a bulk import of someone's library should not abort halfway because one record found
  an edge case, and the exception type in the reason plus the logged traceback keep the bug
  diagnosable.
- Reviewers should resist narrowing the default `import_entry`'s net back to a list of known
  exception types. The list was wrong once already, and it was wrong in a way that passed every
  test written against it, because the tests used a format that raised the exceptions the runner
  expected.
- **A subclass that overrides `import_entry` takes over this decision entirely.** It may narrow the
  net, widen it, or drop it — nothing in `BibFormat` prevents that, per the maintainer's ruling that
  the base class only has to get the job done when its instructions are followed, not police what a
  subclass does instead. A subclass doing so is responsible for FR-013/FR-014/FR-023 holding for its
  own entries; the base class no longer enforces them on its behalf once `import_entry` is replaced.
- **Revisit if** `from_csl_json` ever becomes strict about the shape of its input and raises
  `ValidationError` for everything malformed. The narrow net would then be defensible for content in
  the default implementation, though a format with a bug in it would still escape.
