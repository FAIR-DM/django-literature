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

**Watch item, recorded so the first slow-catalogue report is not diagnosed from scratch.** The cost
of a search scales with the length of the query as well as with the size of the catalogue. A term is
split on whitespace and every word is matched against every one of the eight field paths, three of
which reach contributors through a join, so a ten-word query issues eighty fragment comparisons
across joined tables and then deduplicates. The result page stays bounded — pagination sees to that
— but the scan does not, and nothing the reader can type is capped. This is the accepted consequence
of the decision above and needs no work here. If it ever bites, the answer is the dedicated
text-search facility named above, not a limit on how much someone is allowed to type.

**ADR:** docs/adr/0024-the-catalogue-search-adds-no-index.md

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

**ADR:** none — the search semantics this feature ships, stated for a reader in the README; nothing downstream inherits the choice.

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

**ADR:** none — a field list inside the shared search definition, documented where it is declared.

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

**ADR:** none — one filter's own matching rule, stated in the README and pinned by its tests.

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

**ADR:** none — one filter's own source of choices, carried by the filter class's docstring.

## D6 — Values within a filter widen, filters narrow

**Ambiguous:** how several filters combine, and how several values within one filter combine, was
not stated.

**Chosen:** more than one value within a filter returns references matching any of them; filters
combine with each other and with the search so that a result satisfies all of them.

**Why defensible:** it is what the words mean when read aloud. "Articles or chapters, from 2019"
is one filter widened and another applied, and the opposite convention — requiring a reference to
carry two item types at once — would return nothing, always. This is also the near-universal
convention in faceted search, so a reader arrives already knowing it.

**ADR:** none — the composition rule the README states for a reader; it follows from the filter classes chosen.

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

**ADR:** none — this feature's own behaviour on bad input, stated in the README and covered by tests.

## D8 — One definition of what is searchable, used by both presentations

**Ambiguous:** intake settled that both the table and the card list get the feature. It did not say
whether they share a definition or each carry their own.

**Chosen:** one definition, used by both.

**Why defensible:** two definitions drift, and the drift is silent — a field added to the table's
search and not the card list's produces two catalogues that disagree about what exists, with
nothing failing. The spec makes the agreement testable (FR-023, and the story that compares the two
results) rather than trusting it to review.

**ADR:** docs/adr/0025-one-definition-of-what-the-catalogue-narrows-by.md

## D9 — The contributor page stays as it is

**Ambiguous:** the contributor page is the third place in the front end that lists items, and it is
built on the card list this feature is adding search to.

**Chosen:** it is unchanged, and offers neither search nor filters.

**Why defensible:** the page exists to answer one question — everything this person is credited on
— and a reader who has arrived there has already narrowed the catalogue by contributor. Searching
within it is a different feature with no demand behind it yet. This is the same boundary FS-009
drew when it left the contributor page on cards while the catalogue became a table, and holding the
boundary in the same place twice is worth more than the small convenience of moving it.

Unchanged to a reader is not unchanged in the code: the page subclasses the catalogue today, and the
catalogue is becoming a filtered view. Keeping the page as it is therefore means taking it off that
inheritance and giving it the catalogue's configuration directly, which plan D-6 sets out. Turning
the controls back off from underneath a filtered ancestor is not available — it generates a filterset
over the whole model and raises.

**ADR:** none — a scope boundary, and the mechanism that holds it is recorded in ADR 0025.

## D10 — #88 is absorbed rather than left open

**Ambiguous:** #88 is a separate open issue against the same roadmap item, describing the same
defect this feature must not ship into.

**Chosen:** this feature raises the dependency floor and updates the demo guard, and closes #88.

**Why defensible:** #88's entire remaining content is those two changes, and this feature has to
make both regardless, because filtering discarded on a page move is precisely the defect the
feature exists to remove. Leaving it open would leave a sibling issue describing a floor this
branch has already raised. Sam confirmed the fold at intake.

**ADR:** none — issue housekeeping settled at intake, with no consequence for the code.

## D11 — 0.19.1's pagination change reaches further than research R6 found, and this story does not chase it

**Discovered during US0/T006**, not anticipated at planning. R6 identified one change in the
0.19.0 → 0.19.1 diff: the pagination link template, fixing #88. The release also rewrites
`MVPTableView`'s pagination end to end — `mvp/integrations/django_tables/views.py`'s
`paginate_queryset()` now returns the queryset whole (`return None, None, queryset, False`) rather
than the sliced page Django's `ListView` used to hand it, on the reasoning (from the installed
package's own docstring) that a `django_tables2.Table` is a second paginator over the same rows,
and slicing twice means the row query and every prefetch run again for the second slice.

**Ambiguous:** whether to fix this now, given it breaks two tests this story did not touch and
whose files (`literature/ui/views.py`, `tests/test_ui/test_views.py`) it is not scoped to write.

**Chosen:** confirmed, not fixed, here. `TestItemListView::test_page_holds_no_more_than_paginate_by_items_whatever_the_catalogue_size[literature:item-list]`
and `TestItemTableView::test_paging_to_the_next_page_renders_the_next_rows_under_the_same_headings`
now fail: both assert `len(response.context["object_list"])` directly against the table route, and
`object_list` is no longer sliced — only `context["table"]`'s own page is, and only that page
drives what actually renders (`test_pagination_states_position_and_offers_navigation`, asserting
the rendered `"1-24 of 30"` position line and the `page=2` link, still passes; confirmed by pinning
django-mvp back to 0.19.0 with `pip install "django-mvp==0.19.0"` and back, reproducing and clearing
the two failures on the version alone). Nothing this story owns reads `object_list` off the table
route the way these two tests do, so no task here is blocked by it.

**Why defensible:** the floor bump is R2's own requirement (django-filter's `FilterView` needs it)
independent of #88, and 0.19.1 is still the correct floor — reverting to 0.19.0 to dodge this would
leave #88 open again for no gain, since the object_list change is orthogonal to the link fix. The
two failing tests belong to the story that next touches `ItemTableView` (US-1/T008, which composes
it with `FilterView`) or to whichever one first reads `object_list` off that route rather than the
table's own page — reported in T006's completion evidence for that story to inherit knowingly.

**Revisit if:** US-1/T008 (or whichever story next edits `ItemTableView`) does not already carry a
fix for these two tests — confirm before that story's own baseline check is trusted.

**ADR:** none — a finding about a dependency release, local to this branch's planning.

## D12 — The `issued` annotation states its output field explicitly, rather than inferring it

**Discovered during US0/T007.** The year filter needs `issued__year`, and `annotate_issued()`'s
`Subquery` draws from `ItemDate.begin`, a `PartialDateField` (`django-partial-date`). Inferred from
the source expression, the annotation carries `PartialDateField` as its output field, and
`issued__year=value` raised `FieldError: Unsupported lookup 'year' for PartialDateField` — Django
registers the `year` transform on `DateField`/`DateTimeField` specifically, and `PartialDateField`
subclasses plain `models.Field`; its `get_internal_type() == "DateTimeField"` only tells the schema
editor what database column to create, and is not consulted for lookup resolution.

**Ambiguous:** whether to work around the missing lookup with a `gte`/`lt` half-open range instead,
since every field carries those.

**Chosen:** state `output_field=DateTimeField()` explicitly on the `Subquery`, and keep the plain
`__year` lookup.

**Why defensible:** the `gte`/`lt` range was tried first and returns wrong rows, not just an error —
worse, because it fails silently. `PartialDateField` encodes its precision (year/month/day) in the
stored value's *seconds* component (0/1/2), so a year-only date and a full-date range boundary for
the same calendar year compare unequal at that resolution: reproduced both a real match excluded and
a wrong item included, from the same underlying cause. `output_field=DateTimeField()` changes nothing
about the SQL column — it only tells Django's ORM which field's lookups to resolve against — and
`DateTimeField`'s `year` transform extracts the year in SQL, correctly indifferent to the
seconds-encoded precision. Ordering (`ItemTable.order_issued`, `F("issued")`) is unaffected either
way: it sorts the raw column value, which does not go through a lookup at all.

**Revisit if:** a future filter on `issued` needs month- or day-level precision — the seconds-encoding
gotcha applies there too, and `DateTimeField`'s `month`/`day` transforms will have the same silent
wrong-row failure mode `gte`/`lt` did here if reached for again instead.

**ADR:** none — one annotation's argument, and the reason sits in its own docstring where a reader meets it.

## D13 — The page-2 link already carries the sort at 0.19.1; the standing xfail reads an escaped href

**Discovered while reviewing US0's completion**, which reported that
`TestCatalogueOrdering::test_sort_survives_following_the_rendered_link_to_page_2` (the strict xfail
tracking #88) had not flipped to XPASS on the raised floor, and left it uninvestigated as outside
the story's scope. It is in scope for this feature, because closing #88 is one of the things the
feature promises.

**What is actually true.** Rendered from a request carrying `?sort=-citation_key`, the pagination
component's numbered link to page 2 emits
`href="?sort=-citation_key&amp;page=2"` — measured, not inferred. The upstream fix is present and
working: `{% querystring page=page %}` preserves the rest of the address. The test still fails
because `rendered_page_link()` returns the href verbatim out of the markup, `&amp;` and all, and the
test client then parses that as two parameters named `sort` and `amp;page`. No `page` parameter
reaches the view, page one comes back a second time, and its first row is not less than the first
page's last row.

The helper was written when the emitted href was the bare `?page=2` of the defect it documents, so
no ampersand ever appeared in it and unescaping was never needed. The fix that made #88 go away is
also what first put an entity in that string.

**Chosen:** unescape the href in `rendered_page_link()` (`html.unescape`) and remove the xfail
marker from that test in the same commit. US-3/T017 owns both, and the marker is `strict=True`, so
the suite goes red the moment the helper is corrected — which is the marker doing its job.

**Why defensible:** the assertion, the fixture and the intent of the test are all untouched. What
changes is one line of a helper that was decoding the page's markup incorrectly, and the removal of
a marker whose own stated condition ("flips green once the fix lands and the `ui` floor carries it")
is now met. No pre-existing assertion is weakened to reach it.

**Consequence for T017 and T018, and it is the useful half of this entry.** Every existing test that
follows a rendered pagination link is measuring through this helper, so a search or filter surviving
a page move would fail the same way for the same reason and look like a defect in this feature.
Correct the helper first, then write those tests.

**ADR:** none — a test instrument detail, superseded by the guard the demo story rewrote.

## D14 — US-1 inherits the two `object_list` failures D11 reports, and reinstruments them

**Confirmed at D11's own revisit condition.** Both failures are reproduced at `cc4f638`, and the
cause is exactly as D11 records: at 0.19.1 `MVPTableViewMixin.paginate_queryset()` returns the
queryset whole and republishes `paginator`, `page_obj` and `is_paginated` from the table's own page,
so on the table route `response.context["object_list"]` is the catalogue rather than one page of it.
Upstream states the intent in the method's own docstring — one queryset, one slice, and the sorted
page is the table's — so this is a deliberate contract change, not a defect to report.

**Chosen:** US-1/T008 reinstruments both tests onto the table's own page
(`response.context["table"].page.object_list`), which is where every other assertion about rendered
rows on that route already reads from, and where the count the reader sees comes from. The card-list
route keeps reading `object_list`, which still means a page there.

**Why defensible:** each test's subject is unchanged — a page holds no more than `paginate_by`
references, and page two renders the next rows under the same headings. Only the instrument moves,
from a context variable that no longer describes the rendered page to the one that does. Reading a
stale variable and calling the mismatch a regression would be the actual error.

**ADR:** none — a story-level record of which pre-existing tests moved and why.

## D15 — T008 blocked: turning search and filter on breaks two pre-existing FS-009 tests neither D14 nor any task names

**Discovered during US-1/T008**, by implementing the task exactly as written (`ItemTableView`
composed as `MVPTableViewMixin, FilterView` with `search_fields = SEARCH_FIELDS` and
`filterset_class = ItemFilterSet`, the `actions` override dropped so the mixin's own
`["search", "filter", "create"]` applies) and running the full suite against it. Two tests in
`tests/test_ui/test_views.py::TestItemTableView`, both written for FS-009 and neither named by D14,
fail as a direct and unavoidable consequence:

- `test_carries_no_search_box_filter_control_or_column_chooser` — asserts
  `response.context["table_actions"] == ["create"]`, `'name="q"' not in content` and
  `"filterModal" not in content`. Its own comment cites FS-009's FR-025 (a different requirement
  under that number than this feature's FR-025, which is about the contributor page). This test is
  FS-009's lock on the exact decision D-3 reverses — search and filter switched off, with a test
  guarding that an upstream default could not turn them back on. This feature turning them on by
  design is exactly what trips it.
- `test_column_headers_appear_in_the_required_order` — asserts the six column-header strings appear
  in the rendered page in ascending order of position. `ItemFilterSet.type` is
  `django_filters.ChoiceFilter(label=_("Type"))` (`literature/ui/filters.py`), and the filter
  modal's form (`mvp`'s `cotton/page/list/actions/filter.html`, rendered inside `page.actions`,
  ahead of the table) renders that label as literal text `"Type"` before the table's own "Type"
  column header — confirmed directly: `content.index("Type")` lands inside the modal, earlier than
  `content.index("Citation key")`, which only the table emits.

Both are outside `tests/test_ui/test_views.py`'s D14 allowance and outside every prohibition's
"untouchable" carve-out has an exception for. Confirmed the blast radius is exactly these two beyond
the two D14 already covers: `poetry run pytest -q` full suite, 4 failed / 1628 passed / 1 xfailed,
no other file affected (`test_tables.py`, `test_templates.py`, `test_filters.py`,
`test_contributors.py` all still green).

**Chosen:** not fixed here. The Implementer reverted the production change (`git checkout --
literature/ui/views.py`) rather than land a state where an untouchable pre-existing test is red, and
reports T008 blocked rather than done. T009–T012 all depend on T008's composition existing to be
meaningfully written against, so none were attempted.

**Why defensible:** both tests assert the literal absence of the thing this story exists to add.
`test_carries_no_search_box_filter_control_or_column_chooser`'s premise — search and filter are off
— is the FS-009 decision D-3 explicitly documents as being reversed. Neither test can stay as
written and true at the same time as T008's acceptance criteria; editing either without a
Forge-level decision would be exactly the "special-case code to make a test pass" the craft-tdd
skill prohibits, in the other direction (special-casing the test rather than the code).

**Revisit if:** Forge (or Sam) decides how these two retire — most likely `test_carries_no_search_box_filter_control_or_column_chooser`
is replaced by an assertion of what search/filter now look like on this route (its useful half,
"no column chooser," has no test of its own once the rest is rewritten), and
`test_column_headers_appear_in_the_required_order` is scoped to the table body/headers rather than
the whole rendered page, or the filter form's field order is changed so "Type" is not the first
label a raw substring search finds. Once a decision lands, T008 restarts from here — the production
diff above is not preserved (it was reverted), but the change itself is small and was proven to work
for everything D14 and T008's own acceptance ask of it.

**ADR:** none — a record of a stop during implementation, resolved by D16.

## D16 — D15 resolved: both tests are rewritten, one because its premise is reversed and one because its instrument is wrong

**Decided at the D15 block**, after verifying both findings first-hand rather than accepting the
report. `cotton/page/list/actions/filter.html` renders `filter.form` inline through `c-form`, inside
`page.actions`, which `cotton/page/list/index.html` emits before the body — so every filter label is
literal text on the page ahead of the table, and `ItemFilterSet.type`'s label is `"Type"`. The
column-order finding follows from the upstream markup, not from anything this feature chose.

**Chosen — `test_carries_no_search_box_filter_control_or_column_chooser` is rewritten, not scoped.**
FS-009's FR-025 asserts the absence of exactly what this feature's own FR-001 and FR-009 to FR-013
add, over a signed-off specification. That text is annotated as superseded in place in
`specs/009-tabular-catalogue-view/spec.md`, with its last clause — no column chooser — left standing
as the only part still true. The test follows the requirement: it becomes
`test_carries_search_and_filter_but_no_column_chooser`, asserting `table_actions` equals
`["search", "filter", "create"]` exactly, that `name="q"` and `filterModal` are both present, and
that no column chooser is. It is a closed assertion in both directions, so it still catches an
upstream default widening the surface — the guarantee FS-009 wrote it for is kept, pointed at the
list this feature specifies rather than the one it replaced.

**Chosen — `test_column_headers_appear_in_the_required_order` keeps its subject and moves its
instrument**, exactly as D14 moved the two `object_list` assertions. It reads the table's own header
row rather than the whole rendered page. A page-wide substring search was only ever a proxy for
"the table's columns sit in this order", and it stopped being a faithful one the moment anything
else on the page emitted a matching word. The assertion is not weakened: all six headers must still
be present, and still in that order.

**Why this is mine to decide and not Sam's.** It is a conflict between two of my own specification
documents, where the later one owns the problem and was signed off knowing it reversed the earlier.
Nothing about the feature Sam approved changes. Had the conflict been with a test asserting
something outside the specification's reach, the answer would have been the opposite.

**Not chosen:** reordering `ItemFilterSet`'s fields so `"Type"` is not the first label found. That
fixes the symptom by constraining an unrelated design surface, and the next label collision would
break the test again.

**ADR:** none — resolves D15 by superseding a clause of the earlier spec in place, which is recorded there.

## D17 — T008 blocked again: a third untouchable pre-existing test breaks on the correctly-typed shared `issued` annotation

**Discovered during US-1/T008's second attempt**, resuming after D16's ruling on D15. Implementing
D16's two rewritten tests plus plan D-2/D-3's composition (`ItemTableView(MVPTableViewMixin,
FilterView)`, `search_fields = SEARCH_FIELDS`, `filterset_class = ItemFilterSet`) requires removing
the view's own inline `issued` `Subquery` per plan D-5 ("the annotation moves into the shared
definition and both views carry it") — leaving it in place double-annotates the same alias once
`ItemFilterSet.filter_queryset()` (T007) also annotates it.

Wiring the filterset into the view (rather than instantiating it directly, as `test_filters.py` does)
also surfaced a second, latent bug: `FilterMixin.get_filterset_kwargs()`'s default is `"data":
self.request.GET or None`, and an empty `QueryDict` on a bare, param-less request is falsy, so it
resolves to `None` and the filterset stays unbound. `FilterSet.qs` only calls `filter_queryset()` —
and with it `annotate_issued()` — when bound, so a bare `/catalogue/` load carried no `issued`
annotation at all, contradicting plan D-5's own stated intent ("this runs whether
`annotate_issued()` was called by a caller already or not ... regardless of whether a year was
requested"). Fixed with a view-level override, `ItemTableView.get_filterset_kwargs()`, always passing
`self.request.GET` as `data` — a `QueryDict` `is not None` even when empty — rather than touching
`filters.py`.

With both of those in place, `TestItemTableView::test_the_queryset_annotates_issued_matching_the_items_own_issued_date`
fails, named by neither D14 nor D16's amendment. Confirmed: `AssertionError: assert
datetime.datetime(2020, 5, 1, 0, 0, 2, tzinfo=datetime.timezone.utc) == 2020-05-01` — the annotated
`.issued` is now a raw `datetime` (seconds-encoding the day precision, per D12) rather than the
`PartialDate` the pre-existing test compares it to. Root cause: T007/D12 explicitly typed
`annotate_issued()`'s `Subquery` as `output_field=DateTimeField()`, deliberately overriding the
inferred `PartialDateField` so `issued__year` resolves — a decision already committed and out of this
story's reach (`filters.py` is prohibited). The view's own inline annotation, before T008, carried no
explicit `output_field`, so Django inferred `PartialDateField` from the source expression and
`.issued` round-tripped back to a `PartialDate`, which is what the test was written against. Routing
the view through the shared `annotate_issued()` — exactly as D-5 instructs — is what first exposes
that D12's typing choice and this pre-existing test's assumption disagree. The sibling test,
`test_the_issued_annotation_is_none_for_a_reference_with_no_issued_date`, is unaffected only because
`None == None` holds regardless of type.

Confirmed the blast radius is exactly this one test beyond the four D14/D16 already cover: with the
full T008 change in place, `poetry run pytest -q tests/test_ui/test_views.py tests/test_ui/test_filters.py
tests/test_ui/test_tables.py` — 1 failed (this one) / 250 passed, 1 xfailed; every D14/D16 test and
everything else in those three modules green.

**Chosen:** not fixed here. Reverted the production change and the D16-authorized test rewrites
(`git checkout -- literature/ui/views.py tests/test_ui/test_views.py`) rather than land a state where
an untouchable pre-existing test is red, and report T008 blocked again. T009–T012 depend on T008's
composition existing to be meaningfully written against, so none were attempted this run.

**Why defensible:** `test_the_queryset_annotates_issued_matching_the_items_own_issued_date` is
outside every prohibition's untouchable carve-out — the four named by D14 and D16's amendment are the
complete set. Neither the `get_filterset_kwargs` fix nor the annotation removal is optional: both
follow directly from plan D-2/D-3/D-5 and are necessary for a correct T008 regardless of this one
test. Editing the test without a Forge-level decision would be the same category of error D15 already
stopped for, and changing `annotate_issued()`'s output field to dodge the discrepancy would mean
re-opening D12's already-settled, evidence-backed reasoning (`gte`/`lt` returns wrong rows silently)
from a file this story cannot touch.

**Revisit if:** Forge (or Sam) decides how this one retires — most likely by the same D14/D16
pattern: reinstrumenting the test to assert against what the annotation now actually is (a `datetime`,
per D12), rather than `PartialDate` equality. Once a decision lands, T008 restarts from here — the
production diff (the D-2/D-3/D-5 composition plus the `get_filterset_kwargs` fix) is not preserved
(it was reverted, exactly as D15's was), but it is proven to satisfy every acceptance criterion T008,
D14 and D16 ask of it, plus this one.

**ADR:** none — a record of a stop during implementation, resolved by D18.

## D18 — The `issued` annotation is a raw column value; the test that compares it to a `PartialDate` is reinstrumented

**Ruling on D17.** Verified first-hand rather than taken from the report: `annotate_issued()` on a
reference whose issued date is `2020-05-01` returns
`datetime.datetime(2020, 5, 1, 0, 0, 2, tzinfo=UTC)`, while `ItemDate.begin` reads back as
`PartialDate('2020-05-01')`, and the two compare unequal. D12's `output_field=DateTimeField()` is
what makes the annotation skip `PartialDateField`'s own conversion on the way out.

**D12 stands.** Its alternative was tried and returns wrong rows silently, which is worse than an
error. Nothing in this feature justifies reopening it.

**What the annotation is for.** Two consumers, both internal: `ItemTable.order_issued()` sorts on the
column, and `filter_issued_year()` narrows on it. Nothing renders it — `IssuedColumn` reads the
issued slot off the record's prefetched `item_dates` and hands it to the shared `date_value.html`
partial, precisely so the precision-and-range rule lives in one place. Confirmed in
`literature/ui/tables.py`. So the annotation's Python type is invisible to a reader of the
catalogue, and no user-facing behaviour turns on it.

**Chosen:** reinstrument `TestItemTableView::test_the_queryset_annotates_issued_matching_the_items_own_issued_date`
to compare the annotation's date component against the issued slot's calendar date, rather than
comparing a `datetime` to a `PartialDate`. The test's subject is unchanged and still discriminating:
the reference in it also carries an `accessed` date of `2021-01-01`, so an annotation drawing from
the wrong date slot still fails. Only the instrument moves — the same pattern as D14 and D16, and
for the same reason: a pre-existing test written against an implementation detail that this feature
legitimately changes.

**Two production changes are in scope and required, not deviations.** Both follow from plan D-5 and
neither is stated as its own task, which is why the last run had to reason its way to them:

1. `ItemTableView.get_queryset()` drops its own inline `issued` `Subquery`. The annotation moves into
   the shared definition; leaving the view's copy double-annotates the same alias.
2. `ItemTableView.get_filterset_kwargs()` binds the filterset with `self.request.GET` unconditionally.
   `FilterMixin`'s default is `self.request.GET or None`, and an empty `QueryDict` is falsy, so a
   param-less request left the filterset unbound and `filter_queryset()` — and with it the `issued`
   annotation the sort needs — never ran. The fix lives in the view, not in `filters.py`.

**Standing authority for the rest of this story.** A pre-existing test may be reinstrumented, without
stopping, when all three hold: the production change forcing it is mandated by the plan or this
file; the test's *subject* survives unchanged; and only its instrument moves. Each instance gets its
own entry here and is named in the completion report. A test whose **subject** conflicts with this
feature is still a stop — that is the case D16 ruled on, and it stays mine to rule on.

**Revisit if:** a consumer ever needs to render the `issued` annotation. It is a raw column value
whose seconds component encodes the source date's precision, so rendering it directly would show a
fabricated day and month for a year-only date. Read the `ItemDate` row, as `IssuedColumn` does.

**ADR:** none — a test instrument moving to follow a type stated in D12's own docstring.

## D19 — `type` becomes a `MultipleChoiceFilter`; a widget, not a test edit, absorbs the mismatch

**Ambiguous:** T014 (FR-014) needs one filter that widens to more than one chosen value.
`decisions.md` D6 already names the worked example — "articles or chapters, from 2019" — so `type`
is the filter, but no task states the mechanism, and the brief's own prohibitions name only T013's
language choices and T016's validation as the plausible cases for a `filters.py` change, not this.

**Discovered before committing to it:** converting `type` from `django_filters.ChoiceFilter` to
`MultipleChoiceFilter` breaks `tests/test_ui/test_filters.py::TestItemFilterSetType::test_narrows_to_the_chosen_type`,
a file this story's own scope does not include. That test constructs `ItemFilterSet(data={"type":
ItemType.BOOK}, ...)` with a plain `dict` and a bare stored value — the same call the single-value
filter took — and `forms.SelectMultiple.value_from_datadict()` only calls `.getlist()` (always a
list) against a real `QueryDict`; against a plain `dict` it falls back to `.get()` and returns the
bare value, which `MultipleChoiceField.to_python()` rejects as "not a list." A real HTTP request
never hits this: `self.request.GET` is always a `QueryDict`. Confirmed by running that file, read-only,
before touching `filters.py`.

**Chosen:** `ScalarOrListSelectMultiple(forms.SelectMultiple)`, the `type` filter's own widget,
wraps a bare string in a one-item list. `tests/test_ui/test_filters.py` needed no change and none was
made; `poetry run pytest -q tests/test_ui/test_filters.py` stayed green throughout, confirmed after
the widget landed. Also caught in the same task: the same widget's naive form let `?type=` (an
explicit empty value, the old single-value filter's own no-op) become a list holding one empty
string, which `MultipleChoiceField.validate()` — unlike `ChoiceField.validate()` — rejects outright,
turning "clear the filter" into an empty catalogue under `strict`. The widget also drops blank
entries from the list it returns, restoring the old no-op.

**Why defensible:** the widget only adds acceptance of a bare scalar and drops blanks — it does not
change what a real list of values does, and it was written to keep an out-of-scope test passing
unmodified by construction, not to weaken any assertion. This is additive input handling on the
filter's own public surface, not the "special-case production code to make a test pass" the brief's
prohibitions rule out, which is about narrowing what a test proves, not widening what a filter
accepts. `literature/ui/filters.py` changing outside the two named-plausible cases is stated here and
in the completion report, per the prohibition's own instruction.

**Revisit if:** a second multi-value filter is added — `ScalarOrListSelectMultiple` is written
generically enough to reuse, but has exactly one caller today, so it stays where `type` declares it
rather than moving to a shared module speculatively.

**ADR:** none — a widget local to one filter, with the reason carried in the widget's docstring.

## D20 — `ItemTableView` gains its own `get_context_data()` for `applied_filters`/`applied_filter_count`

**Ambiguous:** T015 (FR-016) asks for what django-mvp's own `applied_filters`/`applied_filter_count`
supply, on the table route. No task states that `ItemTableView` does not already carry them.

**Discovered before writing a test:** confirmed directly that an unfiltered *and* a filtered request
both left `response.context["applied_filters"]` at `None`. The two keys are added by
`MVPFilteredListView.get_context_data()` (`mvp/integrations/django_filters/views.py`), a class this
view does not inherit from — plan.md D-2 composes `ItemTableView` as `MVPTableViewMixin, FilterView`
directly, since no filtered-table equivalent of `MVPFilteredListView` exists. The upstream template
(`cotton/page/list/actions/filter.html`) itself does exactly what it should; it was simply never
given the two keys it reads.

**Chosen:** `ItemTableView.get_context_data()`, four lines, computes the same two keys
`MVPFilteredListView.get_active_filters()` does, read from `self.filterset.form.cleaned_data`. Not
multiple inheritance from `MVPFilteredListView` alongside `MVPTableViewMixin`: both already override
`get_context_data()` and (indirectly, via `MVPListViewMixin`) `get_queryset()`, and resolving that
diamond for four lines of benefit is the abstraction craft-increments' simplicity rule asks to be
justified, not assumed.

**Why defensible:** this is our own view gaining a small, self-contained method — no django-mvp
template touched, no fork, no upstream behaviour changed. The upstream template's own contract
(populate these two keys, get a badge) is met exactly, just from a second call site.

**Revisit if:** a second `MVPTableViewMixin, FilterView` view is added elsewhere in this package —
at that point the four lines are worth lifting into a small mixin of their own, which today would be
a base class for one class, the exact premature abstraction craft-increments warns against.

**ADR:** none — a context key mirrored from the dependency, superseded in part by D21.

## D21 — The applied-filters exclusion of `sort` moves into one shared function

**Discovered before writing T022's own test:** `ItemListView` becoming `MVPFilteredListView` (plan.md
D-2) hands the card list `MVPFilteredListView.get_context_data()`
(`mvp/integrations/django_filters/views.py`), and that upstream method counts every non-empty entry
of `filterset.form.cleaned_data` — exactly the bug D20 already found and corrected on the table. The
hidden `sort` field (`ItemFilterSet.sort`, plan.md D-7) would be counted again, on the card list this
time, and `mvp/templates/cotton/page/list/actions/filter.html` would badge a sort with no filter in
force.

**Chosen:** the exclusion `ItemTableView.get_context_data()` wrote for itself under D20 is extracted
into `get_active_filters(filterset)` in `literature/ui/filters.py` — the module D-1 already names as
the one place a shared definition lives — and both `ItemListView.get_context_data()` and
`ItemTableView.get_context_data()` call it. Not two copies of one exclusion, which is exactly the
duplication FR-023 exists to prevent.

**Why defensible:** this is a production change T022 itself mandates, not a deviation from it — the
finding was known before T022's first test was written. `ItemListView.get_context_data()` still calls
`super()` first (so `MVPFilteredListView`'s own pagination/grid/context wiring runs unchanged) and
only overwrites the two keys the upstream method got wrong for this form.

**Revisit if:** upstream's own `get_active_filters()` grows a way to declare a field as
ordering-only rather than filter-only — at that point this package's own exclusion could be deleted
in favour of it.

**ADR:** none — an extraction inside this feature's own module; the shared function documents itself.

## D22 — The guard reaches page 2 by filtering to the dominant language; the seed grows to make that a real narrowing

**T027 (plan.md D-11) asks which of two routes the guard takes to a second page of a narrowed
result**, at a page size of 24: either the demo's search narrows to something broader than 24 of the
(then) 28 references, or the seed grows so a genuine filter still clears a page.

**A search broad enough to leave 25+ of 28 references is a narrowing in name only.** It would move
the pagination link and pass the guard, but it demonstrates nothing about the feature — a reader
watching the demo would see almost the whole catalogue and no evidence the search filtered anything.
FR-033 asks the guard to exercise a search, a filter and a page move *over a narrowed result*, and a
28-of-28-minus-a-few result does not meet that bar.

**Chosen:** grow the seed and make the language filter the one that reaches page 2. T026 already
tags 26 of the (now 31) references `"en"`, dominant by a wide margin over the four other language
values (`de`, `fr`, `es`, `ja`) the remaining five carry. Filtering to `en` leaves 26 references —
more than the 24-item page, so a reader following the rendered "page 2" link lands on a real second
page of 2 references, of a set genuinely narrowed by language. `test_filtering_to_the_dominant_language_still_leaves_more_than_one_page`
(`tests/test_demo/test_seed.py`) pins the invariant — dominant-language count exceeds
`ItemListView.paginate_by`, read from the view rather than typed out — so a later shrink of the seed
fails there rather than surfacing as a mystifying guard failure in `demo/smoke.py`.

Language is the natural filter for this, over type or contributor: a real catalogue is dominated by
one language, T026 is already rewriting this same file for language values, and no single item type
in the seed clears 24 (the largest, `article-journal`, sits at 11 — measured before T026, confirmed
unchanged after, since none of the three new entries are `article-journal`).

**Why defensible:** every pre-existing assertion in `tests/test_demo/test_seed.py` still passes
(T026's own record); the three added entries are realistic CSL JSON of the same shape as the ones
already there — a French relativity paper, a Spanish novel, a Japanese novel — not filler rows built
to pad a count.

**Revisit if:** the seed's item-type distribution changes such that some other filter clears 24 on
its own — at that point the guard could exercise that filter instead without the seed needing this
much language skew, though there is no reason to change it while the language route already works.

**ADR:** none — how the demo's own check reaches a second page, local to the demo data.
