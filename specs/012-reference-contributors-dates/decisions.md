# Decisions — FS-012

Rationale too long to inline in `spec.md`, plus every ambiguity resolved without escalating.
The spec stands alone; this file records why.

## D1 — Completion, not selection

**Settled at intake.** The obvious design for a contributor field is a searchable select over the
stored names: type a few letters, pick the matching contributor, and the reference links to that
record. It was the first thing proposed and it was wrong.

The failure is not in the widget, it is in what the widget asks. Selecting a stored record asserts
that this reference's contributor is the same person as that record's. The person doing it is
reading a name off a PDF and thinking about the reference, and they will take the first plausible
match — not out of carelessness, but because the interface presented it as the ordinary action and
gave them no reason to think a judgement was being made. When two stored records carry the same
name and belong to different people, that judgement is wrong roughly half the time, invisibly.

Nothing in the record can prevent it. A contributor holds family, given, particles, suffix,
an unparsed form, and three flags a citation processor reads. CSL JSON 1.0.2 defines no author
identifier — there is no ORCID field, no identity of any kind — so two same-named people are two
byte-identical records and no presentation of them can be made to disambiguate.

The alternative considered was to create a record every time and offer no completion at all. That
is correct and tiresome, and the tiresomeness is real: a person maintaining a library retypes the
same collaborator repeatedly.

**Completion resolves it because the two costs turn out to be separable.** A binding select buys
keystrokes and costs correctness. Completion buys the same keystrokes and costs nothing, because
accepting completed text is the same act as typing it. What gets stored is identical either way.

Consequences, accepted:

- Duplicate records accumulate and the interface never offers a way down. This is already the
  catalogue's condition — imports produce duplicates freely, which is precisely why ADR-0017
  exists — so the feature does not introduce it, it declines to solve it here. #112 does.
- Someone who genuinely wants one shared record for a contributor cannot get one through this
  interface. That is where a merge belongs, with every credit visible and a person deciding.
- The error direction is deliberate. A duplicate is recoverable: a merge can join two records
  later and the evidence for the merge is still present. Crediting the wrong person's record is
  not: that record then holds two people's work and unpicking it means re-deciding every credit
  on it individually, with nothing recording which were wrong. **Where identity is ambiguous,
  make the recoverable error.**

This extends ADR-0009 (an import never matches against stored items) and ADR-0017 (identical
stored names are not merged) from reading to entry. Both say the package does not decide two
records describe the same thing. A binding select would have been an exception to that on the one
surface where the consequence is permanent.

This warrants an ADR of its own, proposed at planning, since it governs the write side of the
whole front end rather than this feature alone.

## D2 — The three collections live on the reference form

**Settled at intake.** The alternative was actions on the reference's page, each taking effect
immediately. The deciding case is creating a reference by hand: someone working from the book in
front of them has the authors, the year and the ISBN together, and a form that takes the title and
then sends them back for the authors has split one act into two for no reason visible to them.
Correction runs the same way — an imported reference with a mangled author list and a wrong year is
one repair, not three.

The cost is a larger form, on top of the type-scoped scalar fields FS-008 already put there. Sam
noted that established reference managers commonly divide a form of this size across tabs and that
this may suit the package later. Recorded as an assumption rather than designed for: nothing here
forecloses it, and a single form is the straightforward starting point.

## D3 — Which parts of a contributor a person meets

**Self-resolved.** A contributor record holds nine fields. Presenting all nine is exactly the raw
structure the issue objects to, and three of them —
`comma_suffix`, `static_ordering`, `parse_names` — are signals to a downstream citation processor
about how to render a name. A person entering a reference has no basis on which to set them and no
way to see what setting them would do.

Resolved by two precedents already in the package rather than by a new rule:

- FS-008 kept `categories` and `custom` off the form and required them preserved exactly, because
  they hold content whose shape the person editing cannot reason about. The processor flags are the
  same case, so they get the same treatment (FR-010).
- FS-008 presented the fields that apply and made the rest reachable. Family and given are what a
  person has; particles, suffix and the unparsed form are what some names need. Same shape (FR-009).

## D4 — Stored date content the form does not offer

**Self-resolved.** A date holds a season, a circa flag, a literal form, an unparsed string, and the
raw date parts an import kept when it could not normalize the value. Preserving them is
straightforward (FR-017) and follows FS-008's no-loss guarantee.

The interesting case is the import fallback. When an import cannot read a date it keeps the
original material rather than discarding it, so the catalogue holds dates whose only content is
unparsed. If the form does not show that content, those dates are invisible and unreachable
through the interface — the person sees a reference with no date, and the thing that would let
them fix it is sitting in the record where they cannot get at it.

FS-008 already settled the rule that resolves this: a field already holding a value is always
shown, whatever the type mapping says. Applied to dates it makes an unreadable imported date
repairable, which is a large part of what this feature is for (FR-018).

## D5 — Reordering needs no model change

**Self-resolved.** A contributor's position is numbered within its `(item, role)` group and
assigned when the link is first stored (ADR-0005). It is marked non-editable, which excludes it
from generated forms but places no restriction on what the interface may write. Reordering
therefore means the view assigns positions explicitly, and no field is added, widened or
constrained (FR-039).

Reordering across roles was rejected: positions are numbered independently per role, so there is no
single combined list, and presenting one would imply an ordering the catalogue does not hold.

## D6 — The identifier limits are inherited, and a refusal explains itself

**Self-resolved.** One identifier per kind per reference is a documented design limit rather than
an oversight, and `CONTEXT.md` records that widening it is a feature rather than a fix. Someone
adding a second ISBN nevertheless has to be told something, and a database constraint error is not
it. The refusal names the limit (FR-030).

## D7 — How far the identifier diagnosis goes

**Settled at intake, with the depth delegated.** Every rejection currently returns one message per
kind, giving the shape and an example. The case that is not served is a value of the right shape
with one character mistyped, which fails on a check digit and is the commonest real error — a
transcription slip. It is also the case where an example helps least, because the person's value
already looks like the example.

ISBN and ISSN carry check digits, so those two can distinguish a wrong shape from a wrong
character. DOI, URL, PMID and PMCID carry none, and inventing further diagnosis for them would mean
guessing at what the person meant. Their messages stay as they are (FR-028).

Two bounds on the change, both load-bearing:

- **It is diagnosis only.** No value that passes today fails afterwards and no value that fails
  today passes. The existing validator tests are the guard, and they are expected to pass untouched
  (FR-029, SC-005).
- **It stays at the model layer.** The validators are core, and a project that never installs the
  front end should get the same diagnosis. This is the one part of the feature that is not
  front-end work (FR-037), and it is why the spec cites G7 alongside G4.

## D8 — A person-named kind that matches a known one

**Self-resolved.** Identifier kinds are deliberately open: an unknown kind is stored rather than
rejected, and bypasses format checking (ADR-0002). Meeting that contract in a form creates a gap —
someone who types `isbn` instead of choosing ISBN from the offered set gets an unchecked
identifier, and nothing tells them the check they expected did not happen.

Resolved by matching a typed kind against the known set other than by casing and treating it as
that kind (FR-025). This is an identity assertion, and it is worth naming as one given D1 rejects a
much weaker one. The difference is what is being asserted about: a kind is drawn from a fixed,
enumerated, six-member set the package defines, where `isbn` and `ISBN` cannot denote different
things. A person's name is drawn from an open set where identical spellings routinely do.

## D9 — Same name twice in one role

**Self-resolved.** Each entry creates its own record, so nothing collides with the constraint that
keeps one contributor from appearing twice in a role. It is very likely a slip. It is stored anyway
and nothing warns, for D1's reason: the software does not conclude that two identically-spelled
contributors are one person, and a duplicate is the recoverable direction.

## D10 — A rejected save leaves nothing behind

**Self-resolved.** Contributors are new records, so a naive implementation creates them while
processing the form and orphans them when validation fails elsewhere. The catalogue would then
accumulate contributor records credited on nothing, from saves that never happened, with no way for
anyone to tell them from real ones.

Required explicitly (FR-033) rather than left to the implementation: nothing is written until the
whole edit succeeds, and a rejected save returns the form carrying what was entered.

---

*Decisions below were taken at planning, after the measurements in `research.md`. The design
reasoning behind each is in `plan.md`; what is recorded here is the decision itself.*

## D11 — The check-digit distinction covers ISBN alone

**Taken at planning, and it narrows what the specification gate approved.** The intake session
settled that ISBN and ISSN would both tell a mistyped character from a wrong shape, on the
understanding that both are check-digit types. They are, in the standards. This package acts on only
one of them: `validate_issn` matches a shape and stops, so an ISSN of the right shape with a wrong
check digit is accepted today.

Distinguishing that case means computing the check digit, which turns accepted values into
rejections. FR-029 and SC-005 forbid exactly that, and the suite makes it concrete — `0000-000X` sits
in the accepted-value list and is not a valid ISSN by the standard's arithmetic. A second consumer
would move too: the RIS importer routes an `SN` tag by which of the two validators does not raise.

ISBN separates cleanly and no value moves, so ISBN keeps the distinction. The ISSN gap is real and is
filed as #118, where a change to what the catalogue accepts can be decided on its own terms rather
than arriving inside a feature about form messages.

## D12 — A native element, not a component

The contributor name field is an HTML `<datalist>`: a text input with attached suggestions, where
accepting one writes its text and nothing else happens.

This was expected to be the feature's one external dependency. django-mvp ships no combobox,
autocomplete or enhanced select, and the standing rule sends a gap upstream rather than solving it
locally, so the specification gate carried it as the one risk depending on another repository.

It turned out not to bite, and the reason is worth keeping: **a binding select would have needed a
component, and completion needs an element.** D1 chose completion because binding puts an identity
judgement in front of someone unequipped to make it. That the same choice also removed the
dependency is not a coincidence — the simpler semantics were the correct ones, and simpler semantics
needed less machinery.

## D13 — Reordering is by number, and the affordance is filed upstream

Contributors are reordered by changing a position number, through Django's own formset ordering.
django-mvp has no reordering support and deliberately dropped the Alpine sort plugin from its
bundle, so a drag affordance would mean writing a component this package is not allowed to write.

Recorded rather than left as a silent limitation, because it is the part of this feature a person
will notice and ask about. A drag affordance is raised with django-mvp; when a release carries one,
this becomes a template change and nothing else.

## D14 — The no-loss guarantee is carried into the view

ADR-0021 holds that the server never builds a narrower form, so a hidden field keeps and re-posts its
value and no stored content is discarded by a change of item type. It names its own revisit
condition: a write path that is not the rendered page.

Inline formsets over related rows are that condition. An omitted scalar field is blanked, which is
why the guarantee took the shape it did; an omitted row is simply not there, which is a different
failure with a different fix. So the guarantee is upheld explicitly — a slot holding a value is
always rendered, the parts of a date the form does not offer are never declared and so never
written, and removal is explicit through the formset rather than implied by absence.
