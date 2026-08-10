# ADR-0012 — A format owns its own decoding, and says which file mode it expects

- **Status:** Accepted
- **Context date:** spec 005 (FR-034, Edge Cases), `literature/importers/ris.py` (`RISParser.parse`), `literature/importers/base.py`, issue #23

## Context

The import contract says a format's `parse` receives "an open file object, or anything with a
`read()`". It does not fix a file mode. The BibTeX format assumes text mode and lets its parsing
library own decoding, which worked because nothing in that feature needed the raw bytes.

RIS does need them. A file this decoder cannot read must fail with a reason naming the encoding it
attempted and the byte offset that broke — a message a researcher can act on, given both database
exports carry byte-order marks and legacy exports are often in a Windows code page. Neither piece of
information survives decoding done by the caller.

## Decision

**Decoding happens at the format's own read step, and the format documents the mode it expects.**

`RISParser.parse` reads bytes, decodes them itself, and raises a translated parse error naming the
attempted encoding and the failing offset. That expectation is documented on the method, and every
RIS fixture in the corpus is opened in binary mode.

## Consequences

- Two formats in the same package may expect different modes. That is a documented property of each
  format rather than a contract-wide rule, and it is why the mode belongs in each format's own
  documentation.
- A caller who hands a text-mode file to a format expecting bytes gets that entry's failure reported
  through the result rather than a crash, because the runner catches everything (ADR-0007). The
  message is less legible than a purpose-built one, which is the accepted cost of not adding a
  type check to the contract for a caller disregarding it.
- Nothing was added to the import contract to make this work. The mode expectation lives in the
  format, so a future format is free to make the other choice.
