# ADR-0013 — No copyleft fixture enters this package

- **Status:** Accepted
- **Context date:** spec 005 (FR-030, *Verification corpus*), `tests/data/ris/`, `LICENSE`, issue #23

## Context

This package ships under the MIT licence. Test fixtures are distributed with it: they sit in the
source tree and in the source distribution.

A verification corpus wants real exports (ADR-0010), and real exports are often found inside other
projects' repositories. Those projects have their own licences. The two public corpora holding
genuine RIS book-chapter records — the case this feature could not otherwise evidence, because every
record in the twenty-five permissive baselines is a journal article — are both GPL-3.0, and neither
declares a separate licence for its data files.

## Decision

**A fixture whose licence is incompatible with this package's is not vendored, however useful it is.**
Where that leaves a case unevidenced, the case is reproduced as a constructed fixture, labelled as
constructed, and the substitution is recorded in the specification's *Verification corpus* section.

Reading a licensed file to establish a fact — which tag a producer emits, what shape its records
take — is not redistribution of it, and is allowed. What may not cross the boundary is the file, or
its bibliographic content.

## Consequences

- The book-chapter-with-editors case rests on a constructed fixture written in the shape of the
  producer whose real export leaves the gap. Its structure was learned from a licensed file; its
  bibliographic content is this project's own.
- A permissively licensed fixture may be worth more than a technically better copyleft one. Where a
  choice exists, licence compatibility decides it before quality does.
- Before vendoring anything, its licence is checked and recorded next to it. "Licence to be
  confirmed" is not a state a vendored file may be left in — that phrase sat in this feature's
  research notes for two days and was the reason the check nearly did not happen.
- The rule generalises past this feature: every future corpus in this package follows it, and
  ADR-0014 applies it a second time where the material available is only partly matched.
