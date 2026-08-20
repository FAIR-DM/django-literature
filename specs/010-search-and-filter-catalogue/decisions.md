# Decisions — 010 Find a reference in a large catalogue

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without escalating. The
spec stands alone; this file explains why it says what it says.

## D1 — The feature ships no index, and that is the decision

**Ambiguous:** intake asked for the searched fields to be indexed if they were not already. It did
not say what indexing means for the kind of search this feature performs, and the answer turned out
to change the requirement rather than refine it.

**Chosen:** no index. Raised at the specification gate with what the alternative would actually
cost, and withdrawn there.

**Why defensible:** an ordinary index on a text column orders that column's values, so it serves a
query anchored at the start of a value and cannot serve one looking for a fragment anywhere inside
it. This feature's search is deliberately the second kind — a reader types part of a surname or
part of a title, not its opening characters — so `db_index=True` on the title fields would add a
migration, add write cost on every import of every reference, and change no query plan. It would
also be invisible: nothing fails, the search is exactly as slow as before, and the repository ends
up carrying something that looks like diligence and is decoration.

What would genuinely serve a fragment search is backend-specific and expensive in a way that has
nothing to do with query time. On PostgreSQL it is a trigram index, which means requiring a
database extension; on SQLite, which the test suite and the demo run on, there is no equivalent at
all. A package that needs an extension installed to stay usable at scale is a different package
from one that does not, and turning this one into that is a decision in its own right, not a
detail of a search feature. So it is not taken here.

The filters reach the same answer by a different route. They narrow through the foreign keys
linking contributors and dates to an item, which the framework already indexes, and through item
type and language, whose handful of distinct values across a catalogue give a planner little reason
to use an index even where one exists. There is nothing left worth adding.

The honesty requirement that came with the original reading is dropped with it: the feature claims
nothing anywhere about how fast a search is, so there is nothing to qualify. If the catalogue does
outgrow this, the answer is a real one — a dedicated text-search facility — and it arrives as its
own piece of work with its own decision about what the package requires of its host.

## D2 — Case-insensitive fragments, not whole words

**Ambiguous:** the spec says the search matches text; it did not say whether a term matches a whole
word, a prefix, or any fragment, or whether case matters.

**Chosen:** a fragment appearing anywhere in a value, without regard to case.

**Why defensible:** bibliographic titles are full of hyphenation, possessives, parenthetical
subtitles and non-English orthography, and a whole-word match fails on all of them — someone
searching `ocean` would miss "Palaeo-ocean". A prefix match is worse for names, since a reader
searching a hyphenated or particled surname rarely types its first character. Case-insensitivity is
not a choice so much as the absence of a reason: nobody hunting a reference intends the difference
between `Smith` and `smith`. The cost is the one D1 describes, and paying it knowingly is better
than a fast search that does not find things.

## D3 — Contributor names match on family, given and literal

**Ambiguous:** a `Name` stores its parts separately — family, given, two particle fields, a suffix,
and a literal for organizations and unparsed names. Which parts a search reaches was not settled.

**Chosen:** family name, given name, and literal.

**Why defensible:** those are the three fields that carry a name a reader would type. The literal
matters most and is easiest to overlook: every organizational author in the catalogue — an agency,
a survey, a consortium — is stored there and nowhere else, so omitting it would leave a whole class
of contributor unfindable by name while appearing to work. Particles and suffixes are excluded as
search targets of their own because nobody searches for `van` or `Jr`, and where a particle is
stored inline in a family name it is matched anyway as part of that value.

## D4 — The year filter reads the `issued` slot, and excludes references without one

**Ambiguous:** an item can carry six date slots, and each is partial — a year alone, a year and
month, a full date, or a range. "Year" was not pinned to a slot or a precision.

**Chosen:** the year of the `issued` date. A year-only date qualifies. A range qualifies for the
year it begins in. A reference carrying no issued date is not returned when a year is chosen.

**Why defensible:** `issued` is the date a reference is cited by, the one the table already shows,
and the only one of the six a reader means by "from 2019" without saying so. Accepting year-only
dates is not a concession but the common case: a large share of imported references carry nothing
finer. Excluding undated references follows from what the filter says — a reader asking for 2019 is
asserting something about the date, and a reference with no date does not satisfy it. Sorting made
the opposite choice for undated references, keeping them in the result rather than dropping them,
and the two are consistent: an ordering must account for every reference it orders, while a filter
exists to leave things out.

## D5 — The language filter offers what the catalogue holds

**Ambiguous:** `language` is a free-text field with no `choices`, so its values are whatever the
imported data carried — `en`, `en-GB`, `eng`, `German`, or nothing at all.

**Chosen:** the filter offers the distinct values present in the catalogue, shown as stored, and
treats values differing by case or region subtag as distinct.

**Why defensible:** the alternative is mapping arbitrary strings onto a controlled list of
languages, which means this package adopting a vocabulary it does not own, guessing at values it
cannot parse, and hiding from the reader that their data is inconsistent. Showing what is stored is
honest, needs no vocabulary, and makes an inconsistent import visible as two entries in a filter
rather than invisible behind a normalization. If normalizing language values is worth doing, it is
an import concern and its own piece of work.

## D6 — Values within a filter widen, filters narrow

**Ambiguous:** how several filters combine, and how several values within one filter combine, was
not stated.

**Chosen:** more than one value within a filter returns references matching any of them; filters
combine with each other and with the search so that a result satisfies all of them.

**Why defensible:** it is what the words mean when read aloud. "Articles or chapters, from 2019"
is one filter widened and another applied, and the opposite convention — requiring a reference to
carry two item types at once — would return nothing, always. This is also the near-universal
convention in faceted search, so a reader arrives already knowing it.

## D7 — An invalid or empty filter says nothing matched, rather than falling back

**Ambiguous:** what happens when the address carries a filter value that no reference has, or one
that was never valid — a hand-edited address, a stale bookmark, a language deleted from the
catalogue.

**Chosen:** it narrows to nothing and says so. Never an error, and never a silent fall back to the
unfiltered catalogue.

**Why defensible:** the failure mode of falling back is that a reader is shown a full page they did
not ask for with no indication that their filter was discarded, and reasonably reads it as the
result. That is the same fault as the pagination defect this feature closes: state silently
dropped, with a plausible page in its place. Raising an error is the other extreme and punishes a
reader for a stale bookmark. Reporting no matches is true in both cases — nothing in the catalogue
matches what was asked for — and leaves the controls on the page so the reader can change it.

## D8 — One definition of what is searchable, used by both presentations

**Ambiguous:** intake settled that both the table and the card list get the feature. It did not say
whether they share a definition or each carry their own.

**Chosen:** one definition, used by both.

**Why defensible:** two definitions drift, and the drift is silent — a field added to the table's
search and not the card list's produces two catalogues that disagree about what exists, with
nothing failing. The spec makes the agreement testable (FR-023, and the story that compares the two
results) rather than trusting it to review.

## D9 — The contributor page stays as it is

**Ambiguous:** the contributor page is the third place in the front end that lists items, and it is
built on the card list this feature is adding search to.

**Chosen:** it is unchanged, and offers neither search nor filters.

**Why defensible:** the page exists to answer one question — everything this person is credited on
— and a reader who has arrived there has already narrowed the catalogue by contributor. Searching
within it is a different feature with no demand behind it yet. This is the same boundary FS-009
drew when it left the contributor page on cards while the catalogue became a table, and holding the
boundary in the same place twice is worth more than the small convenience of moving it.

## D10 — #88 is absorbed rather than left open

**Ambiguous:** #88 is a separate open issue against the same roadmap item, describing the same
defect this feature must not ship into.

**Chosen:** this feature raises the dependency floor and updates the demo guard, and closes #88.

**Why defensible:** #88's entire remaining content is those two changes, and this feature has to
make both regardless, because filtering discarded on a page move is precisely the defect the
feature exists to remove. Leaving it open would leave a sibling issue describing a floor this
branch has already raised. Sam confirmed the fold at intake.
