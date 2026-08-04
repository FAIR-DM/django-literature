# ADR-0007 — The import runner catches every exception, not a named few

- **Status:** Accepted
- **Context date:** spec 003 (FR-013, FR-014, FR-023), `literature/importers/runner.py`, issue #21

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

Both `except` clauses catch `Exception`. Any exception raised while converting or storing one entry
becomes that entry's failure, and the run continues.

Two things keep this from hiding real bugs:

- When the exception is not one the contract knows about, its type is named in the reason
  (`KeyError: author`), so a defect in a format or in this package does not masquerade as bad file
  content.
- Every caught exception is logged with `exc_info=True`, so the traceback is available to whoever
  goes looking.

This is what `django-import-export` does at its row boundary, for the same reason.

## Consequences

- The contract's promise is now true for any input, rather than for the subset of malformed input
  whose failure mode was anticipated.
- **A genuine bug in a format, or in this package, is reported as a failed entry rather than
  crashing loudly.** That is the real cost and it is accepted knowingly: a bulk import of someone's
  library should not abort halfway because one record found an edge case, and the exception type in
  the reason plus the logged traceback keep the bug diagnosable.
- Reviewers should resist narrowing this back to a list of known exception types. The list was
  wrong once already, and it was wrong in a way that passed every test written against it, because
  the tests used a format that raised the exceptions the runner expected.
- **Revisit if** `from_csl_json` ever becomes strict about the shape of its input and raises
  `ValidationError` for everything malformed. The narrow net would then be defensible for content,
  though a format with a bug in it would still escape.
