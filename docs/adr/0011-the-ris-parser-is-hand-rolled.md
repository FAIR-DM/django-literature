# ADR-0011 — The RIS parser is hand-rolled, and takes no parsing library

- **Status:** Accepted
- **Context date:** spec 005 (FR-006 through FR-010, FR-018), `literature/importers/ris.py`, issue #23

## Context

The BibTeX format depends on `bibtexparser`, which set a precedent: a format takes a parsing library
and adapts its output. The equivalent library for RIS is `rispy`, and following the precedent would
have been the default choice.

`rispy` was installed and run against this feature's own requirements rather than assessed from its
documentation.

## Decision

**The RIS parser is written in this package and adds no runtime dependency.**

`rispy` fails four requirements outright, and none of the failures is configurable:

- A file whose final entry is missing its closing tag loses that entry silently.
- Material before the first entry is discarded silently, as is a tag block carrying no reference
  type — both of which this package must report rather than drop.
- Repeated values are discarded by default.
- A file carrying a byte-order mark returns zero records, and both database exports this feature
  targets emit one.
- Its parse error type is exported but never raised, so a file that is not RIS at all comes back as
  an empty list with no error.

The common thread is a recovery strategy: resynchronise quietly and return what survived. This
package's contract is the opposite — report what happened to every entry — so the disagreement is
architectural rather than a matter of options. Working around it would mean replacing its one parsing
method, and preserving raw tags means discarding its tag table, which is the only asset left after
that.

## Consequences

- This package owns RIS parsing bugs. That is the real cost, and it is accepted deliberately: the
  parser is small, and the behaviour it must have is the behaviour the requirements name.
- The parser hands over raw tags in source order rather than friendly field names, so no third naming
  layer sits between an RIS tag and a CSL variable.
- The precedent is now that a format takes a library when the library's error behaviour matches the
  contract, and hand-rolls when it does not. `bibtexparser` remains the right call for BibTeX.

## Revisit if

`rispy` changes its recovery behaviour so that unclosed entries, header material, reference-type-less
blocks and repeated values are all reportable. That would make the dependency worth reopening.
