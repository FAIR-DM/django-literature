# ADR 0031 — Completion suggests a spelling, never a record

**Status:** accepted

## Decision

Where the front end helps someone enter a name that already exists in the catalogue, it completes
the *text* and never links to the *record*. Accepting a suggestion is the same act as typing the
same characters: a new record is created, and the record the suggestion was drawn from is not
touched, not linked to, and not consulted again.

The mechanism is a plain HTML `<datalist>`, a text input with attached suggestions, rather than a
select, a combobox or any component that carries an identifier alongside the text. That is not an
implementation detail to be swapped later. A control that posts an identifier is a different
decision, not a different rendering of this one.

This governs the write side of the front end generally, not one field on one form.

## Why

The obvious design is a searchable select over stored names: type a few letters, pick the match,
link the reference to that record. It buys keystrokes and costs correctness, and the cost is
invisible.

Selecting a stored record asserts that this reference's contributor is the same person as that
record's. The person doing it is reading a name off a PDF and thinking about the reference. They
will take the first plausible match, not carelessly, but because the interface presented it as the
ordinary action and gave them no reason to think a judgement was being asked for. Where two stored
records carry the same name and belong to different people, that judgement is wrong about half the
time, and nothing afterwards records that it was made.

Nothing in the data can prevent it. CSL JSON 1.0.2 defines no author identifier at all, no ORCID
and no identity of any other kind, so two same-named people are two byte-identical records, and no
presentation of them can be made to disambiguate.

Completion resolves it because the two costs turn out to be separable. A binding select buys
keystrokes and costs correctness. Completion buys the same keystrokes and costs nothing, because
what gets stored is identical whether the text was typed or accepted.

The general rule underneath, which is the part worth carrying forward: **where identity is
ambiguous, make the recoverable error.** A duplicate record can be joined later, and the evidence
for joining it is still present. Crediting the wrong person's record cannot be undone in the same
way. That record then holds two people's work, and unpicking it means re-deciding every credit on
it individually, with nothing recording which were wrong.

This extends ADR-0009 (an import never matches against stored items) and ADR-0017 (identical stored
names are not merged) from reading to entry. Both hold that the package does not decide two records
describe the same thing. A binding select would have been an exception to that on the one surface
where the consequence is permanent.

There is a second, quieter consequence. A binding select would have needed a component the package
does not have and is not allowed to write, while completion needs an element the browser already
ships. The simpler semantics were the correct ones, and they turned out to need less machinery. The
absence of a dependency here is a symptom of the decision being right, not a separate piece of luck.

## What this rules out

- Duplicate records accumulate, and this interface offers no way down. That is already the
  catalogue's condition, since imports produce duplicates freely, which is why ADR-0017 exists.
  This decision declines to solve it here rather than introducing it.
- Someone who genuinely wants one shared record for a contributor cannot get one this way. Joining
  records belongs in a deliberate merge, with every credit visible and a person deciding.
- Entering the same name twice in one role stores two records and warns about nothing. It is very
  likely a slip, and it is still the recoverable direction.

## Revisit if

CSL gains a contributor identifier, or the package grows a merge with its own interface. Either
makes identity something the data can carry rather than something the person is being asked to
assert, and a binding control stops being a trap at that point.

Note the boundary this does not cross. A kind drawn from a fixed, enumerated set the package itself
defines is not this case: `isbn` and `ISBN` cannot denote different things, so matching a typed
identifier kind against the known set other than by casing is a safe assertion. The rule here is
about open sets, where identical spellings routinely denote different things.
