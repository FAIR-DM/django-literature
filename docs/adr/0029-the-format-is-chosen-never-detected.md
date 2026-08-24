# ADR-0029 — The format is chosen, never detected

- **Status:** Accepted
- **Context date:** spec 011 (FR-005, FR-007), `literature/ui/forms.py`, issue #50

## Context

The import page could work out which bibliography format a file is written in, from its extension or
from its opening bytes, rather than asking the reader. Most tools that read bibliography files offer
exactly that, usually as the default.

## Decision

The reader chooses the format from a list. The package does not look at the file to work it out, and
does not offer detection as an option.

The list is read from the installation's configured formats rather than written into the interface,
so a project that adds a format gets it in the list without this page being revisited.

## Consequences

- Detection fails silently in the one case that matters. A file whose extension or opening lines
  suggest one format while its body is another is imported as the wrong thing, and what comes back
  is a set of entries reported as created and quietly wrong. Choosing wrongly, by contrast, is
  reported: the format itself says "No BibTeX entries found. Is this a BibTeX file?" on every entry,
  through the ordinary report rather than as an error, so the reader is told rather than misled.
- This is the same argument that settled reading BibLaTeX as classic BibTeX (spec 004): a refusal a
  reader can act on beats a silent misreading.
- A reader who does not know what their file is has to find out. That cost is real and is accepted:
  it falls on the one person in the exchange who can actually resolve it.
- Nothing in the package may inspect an uploaded file's content to make a routing decision, which
  also rules out an extension or content-type allowlist on the upload (ADR-0030).
