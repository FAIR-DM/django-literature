# Decisions — 006 Browse the Reference Catalogue in an Opt-In Front End

Rationale that would not fit inline in `spec.md`, plus every ambiguity resolved without escalating.
Each decision names what was ambiguous, what was chosen, and why the choice is defensible.

## D1 — The list orders by most recently added, not by issued date

**Ambiguity**: Intake settled that the list ships with one fixed order and named "newest issued date
first" as an example rather than a ruling. An issued date is not a field on the item: it is an
`ItemDate` in the `issued` slot, backed by partial-date fields, so it may be a year alone, a
year and month, a full date, or a range with a `begin` and an `end` — and an item may carry no
issued date at all.

**Chosen**: The catalogue's declared default order, most recently added first, which is what the
store already orders by.

**Why defensible**: Ordering by issued date forces a set of reader-visible rulings this feature has
no reason to make — whether a year-only 1998 sorts before or after a full date in 1998, which end of
a range a range sorts on, and whether items with no issued date collect at the top or the bottom.
Issue #49 owns reader-chosen ordering and will have to answer all three when it offers a choice. A
package that answers them once here and again there ends up with two orders that disagree, and the
disagreement surfaces as a reader noticing the list reshuffles when they touch a control. Reusing
the store's own declared default keeps one answer in the package, and costs nothing a reader asked
for: nobody has requested an issued-date order, and #49 is where they would get it.

## D2 — A reference page is addressed by primary key, never by citation key

**Ambiguity**: The citation key is the human-facing handle for an item and the obvious candidate for
a readable URL.

**Chosen**: The primary key addresses the page. The citation key is displayed on both pages and
never used to address one.

**Why defensible**: `CONTEXT.md` is explicit that a citation key is indexed but **not** globally
unique — uniqueness is resolved per import batch, with `from_csl_json` suffixing collisions. Two
items may therefore share a key across batches. Addressing a page by it would either resolve to an
arbitrary one of several items or require a uniqueness the model does not have and this feature has
no mandate to add. Readable URLs are a real want, but they are a change to the store's key
semantics, which is a feature of its own.

## D3 — A list entry carries the citation key

**Ambiguity**: Whether the citation key belongs in the list at all, or only on the reference page.

**Chosen**: It appears on both.

**Why defensible**: It is the handle a reader already uses to refer to an item, and it is often the
only thing distinguishing two entries in a catalogue holding several editions or several papers by
the same authors in the same year. Leaving it to the reference page means the reader has to open
candidates one at a time to find the one they meant.

## D4 — A contributor has a page of their own

**Reversed at the specification gate, 2026-08-11.** The original decision is kept below, because the
reasoning that produced it is what the reversal answers.

~~**Chosen**: Out of scope. Contributors are shown on the reference page and are not themselves
navigable. The request names one list and one reference page, and no sibling issue in R6 owns a
contributor view, so building it here is new scope rather than a slice of agreed scope, and it would
set the boundary against #49's filtering by contributor without that feature having a say.~~

**Ambiguity**: A `Name` is stored shared across items, so a page collecting everything one
contributor worked on is a small step from the reference page. The scan ruled it out as unrequested.
At the gate the maintainer asked for it directly, which settles the "unrequested" half of that
reasoning and leaves the boundary question against #49 open.

**Chosen**: In scope, as User Story 4. A contributor's name on a reference page links to that
contributor's page, which shows the name as stored and the items they are credited on with the role
they held on each, paginated and ordered as the catalogue is.

**Why defensible**: The boundary against #49 holds, and it is a difference in kind rather than a line
drawn for convenience. This page is a destination reached by following a link from a reference the
reader is already looking at, and it answers a question the store can answer directly, since
contributors are stored once and shared. #49 is a query surface: text search over the catalogue and
facets the reader chooses, of which contributor is one. The two can coexist without either owning
the other, and #49 may later link into these pages rather than reimplementing them.

Priority P4 rather than P3: it is the only story none of the others depend on, so it is the last
built and the cheapest to lose if the run is cut short. The opt-in guarantee stays at P3 because it
is a property that has to hold from the moment the app exists, and adding surface before it is
verified is how it gets lost.

## D7 — Identical stored names are not merged

**Ambiguity**: The contributor page makes the store's lack of name de-duplication visible for the
first time. Two `Name` records holding the same family and given values are two records, so a person
imported from two different files has two pages, each showing half their work.

**Chosen**: The interface reports the store. Identical names keep separate pages, and no attempt is
made to decide that two records are the same person.

**Why defensible**: Merging is authorship disambiguation, which is a research problem in its own
right and one that established reference managers get wrong regularly. Guessing it inside a browse
page would make the interface assert something the catalogue does not hold, and the reader would
have no way to see that a merge had happened or to correct it. Reporting the store keeps the page
honest, and it leaves de-duplication available as a feature that can be specified properly, with the
maintainer deciding what evidence justifies a merge.

## D5 — Opt-in is enforced by the dependency graph, not by convention

**Ambiguity**: "Opt-in" could mean only that a host chooses whether to add the app to
`INSTALLED_APPS`, with django-mvp installed either way.

**Chosen**: django-mvp arrives through an optional extra. A core-only install resolves no front-end
package.

**Why defensible**: The README's second tie-break principle is that the core stays UI-free so that
"embedding the core never drags in the UI stack", and the R6 deliverable is a core "carrying no
front-end dependency". A convention-only separation satisfies neither: the host still pays the
install, the transitive dependency still appears in its lock file and its vulnerability surface, and
the separation degrades silently the first time something in the core imports from the app. Making
it a dependency-graph property means US3 can be verified mechanically rather than reviewed by eye.

## D6 — A local component is a bridge, and the specification tracks it

**Ambiguity**: The composition rule inherited from django-accounts-center forbids custom components,
but Sam's answer at intake allows filling a gap locally until an upstream django-mvp release carries
the component. Without a record, a temporary bridge is indistinguishable from the custom component
the rule exists to prevent, and it survives by being forgotten.

**Chosen**: FR-009 requires the need to be raised before anything is built, the gap to be filed
upstream, and every local stand-in to be listed in the specification's *Component gaps* section with
its upstream request.

**Why defensible**: It keeps the rule enforceable without blocking the run on an upstream release
cycle. The section is empty at specification time, so its contents at merge are exactly the debt
this feature took on, named and with a stated exit — which is the standing requirement that
technical debt is deliberate and its cost named, rather than accumulated by accident.

## D7 — The scalar-field helper ships inside the UI app, not the core

**Ambiguity**: The helper that walks an item's non-empty scalar fields duplicates an idiom already
in-line in three places in the core, which reads as an argument for putting it in `literature/utils/`.

**Chosen**: `literature/ui/fields.py`, beside its only caller. The three in-line copies stay as they
are, and deduplicating them stays a follow-up.

**Why defensible**: The deduplication is the only thing that would justify a core module, and the
same decision declines to do it — so the core would gain a module shipped to every core-only
consumer with one caller inside an optional app. That contradicts FR-006, which exists to keep this
feature out of the core entirely, and Article III, which forbids indirection without a present second
use. If the three copies are ever unified, the helper moves to `utils/` then, with the second caller
that earns it.

## D8 — SC-002 states documented steps, not "one app" *(amended after the design review, 2026-08-11)*

**Ambiguity**: The specification as approved said the host adds ~~one app~~ and gets a working
interface with ~~no further configuration~~. Planning research then established what django-mvp
actually requires of a host: `django.contrib.sites`, `django.contrib.staticfiles`, `django_cotton`,
`easy_icons`, `flex_menu` and `mvp` in `INSTALLED_APPS`, the `mvp_config` context processor, `SITE_ID`
and the sites middleware. As written, SC-002 and User Story 3's third acceptance scenario were not
achievable and no task could carry them.

**Chosen**: Both restate the host's step as *following the documented install steps*, and T023 makes
the README the single place those steps live. The guarantee that survives is the one the criterion
was written to protect: the host writes no view, no template, no URL pattern and no styling. FR-004
is clarified in the same pass — it means the app introduces no settings of its own, not that its
dependencies install themselves.

**Why defensible**: The alternative is an app that configures its host, by mutating `INSTALLED_APPS`
or shipping a settings module for it to import. That is worse than the documentation it replaces: it
takes decisions away from the project that owns them, it is invisible where a reader looks for it,
and it makes an embeddable package non-embeddable — the opposite of Article X. The criterion was
measuring the wrong thing, so the criterion is what changed.

**Recorded for veto**: this amends text approved at the specification gate. The scope, the pages and
the guarantee are unchanged.
