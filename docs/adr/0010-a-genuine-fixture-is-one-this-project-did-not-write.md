# ADR-0010 — A genuine fixture is one this project did not write

- **Status:** Accepted
- **Context date:** spec 005 (FR-030, *Verification corpus*), `tests/data/ris/`, issue #23

## Context

An importer is only as trustworthy as the files it has been proven against. Hand-written fixtures
test the rules somebody thought of; real exports carry the malformations nobody thought of, which is
where import bugs actually live.

But real exports are awkward to obtain. Desktop reference managers are licensed software, and the
two large citation databases need institutional subscriptions. A corpus requirement that can only be
met by holding a subscription is a requirement that quietly stops being met.

## Decision

**A fixture is genuine when the producer's own code wrote it — regardless of who published it.** A
file the producer publishes counts. A file a third party publishes from a producer's output counts.
What disqualifies a file is this project having written it.

Two rules keep that honest:

- A constructed file is never presented as a genuine export. The corpus separates the two on disk,
  and each directory's README says which it holds.
- Where no genuine file can be obtained for a producer, that producer's coverage rests on a fixture
  built from its published tag documentation, and the specification's *Verification corpus* section
  records which producer that applies to. The corpus never overstates what has been proven.

## Consequences

- The corpus is reproducible and offline. No test reaches the network, and no contributor needs a
  subscription to run the suite.
- Vendored files carry their provenance: origin, licence and retrieval date, recorded next to them.
- Where a case is evidenced by a constructed file rather than a real one, that is written down as a
  substitution rather than left implicit (ADR-0013 records one such case, and ADR-0014 the rule for
  a corpus that is only partly matched).
- A fixture's shape may be copied from a real export to make it faithful; its bibliographic content
  is the project's own.
