# ADR-0014 — Cross-producer equivalence is proved over the material that exists, and labelled where it does not

- **Status:** Accepted
- **Context date:** spec 005 (SC-005, FR-029, FR-030, *Verification corpus*, Refinements 2026-08-05), `tests/data/ris/`, issue #23

## Context

A claim that several producers' exports of the same references import to equivalent items needs
files that actually hold the same references. This feature's research recorded that a public corpus
publishes "the same ten references exported through twenty-five tools", and the specification and the
task graph were both written on that basis.

It was false in the part that mattered. The corpus does publish one matched set of ten references —
across six exporting tools — but the two large citation databases publish *different* reference sets,
sharing nothing with the matched set or with each other. The equivalence assertion was therefore
impossible to write against the three files it named, which the implementation reported as blocked
rather than working around.

The finding is worth recording for its shape as much as its content: a research claim the
specification had already absorbed turned out to be wrong, and everything downstream had inherited
it, including a commit message that repeated the claim rather than checking it.

## Decision

**An equivalence claim is evidenced by genuine files wherever a matched genuine set exists, and by
constructed re-encodings where it does not. Which half covers which producer is written down.**

The construction rules are what keep this from becoming circular:

- A constructed equivalence file is derived from a genuine file's records, carrying only the fields
  the claim judges.
- Each producer's conventions are taken from *that producer's own genuine export*, not from its
  documentation, so the re-encoding reflects what the tool really emits.
- No identifier is invented. A field that would have to be fabricated rather than re-encoded — a
  database's own record URI or accession number — is left out.
- Genuine files stay in the corpus unchanged and keep carrying every producer-convention test they
  already carried. The constructed files serve the equivalence claim alone.

## Consequences

- The claim is weaker than "three genuine exports agree", and it says so. What is genuine is the
  agreement between two real producers; what is constructed is the two database encodings.
- Divergences that are really in the data are asserted one by one rather than smoothed away by a
  lenient comparison — differing identifier packing and initial punctuation among them.
- A research finding the specification depends on is a claim to be tested before it becomes evidence,
  not a fact because it is written down. This one was corrected in place, with the original struck
  through rather than deleted, so the correction is visible to anyone who read the earlier version.
- Where a genuine matched export later becomes available, it replaces the constructed half and this
  ADR is what says why the constructed half was there.
