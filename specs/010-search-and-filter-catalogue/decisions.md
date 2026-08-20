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

Unchanged to a reader is not unchanged in the code: the page subclasses the catalogue today, and the
catalogue is becoming a filtered view. Keeping the page as it is therefore means taking it off that
inheritance and giving it the catalogue's configuration directly, which plan D-6 sets out. Turning
the controls back off from underneath a filtered ancestor is not available — it generates a filterset
over the whole model and raises.

## D10 — #88 is absorbed rather than left open

**Ambiguous:** #88 is a separate open issue against the same roadmap item, describing the same
defect this feature must not ship into.

**Chosen:** this feature raises the dependency floor and updates the demo guard, and closes #88.

**Why defensible:** #88's entire remaining content is those two changes, and this feature has to
make both regardless, because filtering discarded on a page move is precisely the defect the
feature exists to remove. Leaving it open would leave a sibling issue describing a floor this
branch has already raised. Sam confirmed the fold at intake.

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
