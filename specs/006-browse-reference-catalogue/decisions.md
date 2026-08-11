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

**ADR:** none — the specification states the order, and issue #49 owns reader-chosen ordering when it lands.

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

**ADR:** docs/adr/0015-a-reference-page-is-addressed-by-primary-key.md

## D3 — A list entry carries the citation key
**Ambiguity**: Whether the citation key belongs in the list at all, or only on the reference page.

**Chosen**: It appears on both.

**Why defensible**: It is the handle a reader already uses to refer to an item, and it is often the
only thing distinguishing two entries in a catalogue holding several editions or several papers by
the same authors in the same year. Leaving it to the reference page means the reader has to open
candidates one at a time to find the one they meant.

**ADR:** none — a presentation choice the specification carries as FR-013.

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

**ADR:** none — a scope decision, settled at the specification gate and recorded there.

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

**ADR:** docs/adr/0017-identical-stored-names-are-not-merged.md

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

**ADR:** docs/adr/0016-the-front-end-arrives-through-an-optional-extra.md

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

**ADR:** none — the binding rule (django-mvp is the one adopted UI layer) now lives in the constitution's UI clause, and the tracking mechanism is this specification's FR-009.

## D9 — The scalar-field helper ships inside the UI app, not the core
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

**ADR:** none — where one helper file sits, with one caller, inside the boundary ADR-0016 already draws.

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

**ADR:** none — an amendment to this feature's own success criterion, recorded in the specification it amends.

## D10 — `literature/ui/urls.py` binds placeholder views, not `literature.ui.views`
**Ambiguity**: T006 (foundational) creates `literature/ui/urls.py` with three named, reversible
routes. The views those routes name — `ItemListView`, `ItemDetailView`, `ContributorDetailView` —
are built later, one per story, in `literature/ui/views.py`, which the foundational phase does not
create (the prohibition on writing view classes here exists precisely so a later story does not
collide with content this phase already wrote). `path()` needs a real callable at import time,
so the routes cannot name a module or symbol that does not exist yet.

**Chosen**: each route binds to `django.views.generic.View` — a real, working, but content-free
Django class, not one from this feature. The route names, patterns and namespace are final;
nothing in this file names a symbol from `literature.ui.views`. When US-1, US-2 and US-4 add their
real view classes, each story's own task should update its one corresponding `path()` line to
point at it — a single-line, non-conflicting edit across three independent branches, not a shared
symbol three stories would otherwise define independently (the actual "merge conflict at
convergence" the views.py/tests_views.py prohibition is guarding against).

**Why defensible**: `reverse()` only needs the URLconf to load and the pattern names to exist; it
never invokes the view. Django's own generic `View` is the cheapest table-stakes callable that
satisfies that without inventing a bespoke deferred-import mechanism or writing anything that
looks like this feature's actual view logic. The alternative — a small lazy-dispatch wrapper that
imports `literature.ui.views` at request time instead of import time — would remove the follow-up
edit entirely, but at the cost of a mechanism nothing else in this codebase uses and that solves a
problem only if the four stories are dispatched from four independent branches off the same base
commit rather than sequentially from each other's accepted work; either way, three one-line edits
to already-distinct routes is a cost worth accepting over speculative machinery for an unconfirmed
orchestration detail (Article III).

**Revisit if**: a later story's implementer finds `literature/ui/urls.py` unexpectedly conflicts
across two of US-1/US-2/US-4's branches at convergence — that would mean the "single-line,
non-conflicting edit" assumption above was wrong, and the lazy-dispatch alternative should be
built instead.

**ADR:** none — a sequencing device for the run; the routes bind their real views now and nothing downstream inherits it.

## D11 — `T006` executed before `T004` in this session
**Ambiguity**: the brief lists tasks `T001`–`T006` in that order, and T004's own task text ("mount
the app in tests/urls.py at a prefix") depends on `literature/ui/urls.py` existing, which T006
creates. T006's acceptance ("each name reverses... under the mounted prefix") does not, in turn,
depend on T004: it builds its own throwaway `ROOT_URLCONF` via `override_settings`, so it never
needed T004's mount to exist. The dependency runs one way.

**Chosen**: implemented T006 before completing T004, each still as its own complete, independently
green, independently committed slice with its own tests — the task boundaries and acceptance
criteria are unchanged, only the order they were executed and committed in.

**Why defensible**: both tasks belong to this same story (US0); there is no cross-story boundary
here of the kind the prohibitions protect (US-1/US-2/US-3/US-4 never touch either file). Craft
increments' "risk first" guidance is to resolve a task other tasks depend on before the tasks that
depend on it, which is exactly this case.

**Revisit if**: never — this is a within-story execution-order note, not a standing rule.

**ADR:** none — a within-story execution-order note.

## D12 — `tests/test_ui/conftest.py` ships one populated-item fixture, not a bespoke `client`
**Ambiguity**: T004 directs this file to hold "the client and item fixtures T009, T013 and T020
share, so no story owns them" — but those three tasks belong to US-1, US-2 and US-4, dispatched
after this story, and their own task text (read only for this sequencing question, per the note in
`progress.md`) does not specify what either fixture needs to look like.

**Chosen**: one `populated_item` fixture — a saved `Item` with one `ItemName`, one `ItemDate` and
one `ItemIdentifier`, wrapping the four factories `tests/conftest.py` already exposes individually.
No bespoke `client` fixture: pytest-django's own `client` fixture (a plain `django.test.Client`)
is already available to every test in the tree without redeclaration, and the three routes it
would hit (`literature:item-list`, `literature:item-detail`, `literature:contributor-detail`) need
nothing session-specific — the pages are open by default (S0 intake, question 4).

**Why defensible**: `populated_item` is the one composition every one of the three pages plausibly
renders against (a row with a contributor, a date and an identifier, not a bare item), built from
existing factories rather than a new one. Declaring a `client` fixture that only re-wraps
`django.test.Client()` with no added behaviour is the redundant abstraction craft-increments'
Simplicity First rules out.

**Revisit if**: US-1, US-2 or US-4's own implementer finds this fixture does not match what their
task actually needs (a different combination of related records, or a genuine reason for a
non-default client) — flagged as a concern in this story's completion report for Forge to confirm
before those stories dispatch, since "no story owns them" only holds if what is here is actually
sufficient.

**ADR:** none — a test-fixture choice local to this feature's test package.

## D13 — Two test-infrastructure files created ahead of the task that names them
**Ambiguity**: two of this story's test files have no natural single-task owner. `tests/test_ui/__init__.py`
is T004's stated deliverable (Article XIV), but T002 is the first task that needs
`tests/test_ui/` to exist as a collectible package, three tasks earlier. `tests/test_ui/test_templates.py`
is where T003's own base-template test lives (no source module to mirror it against — the
`literature/ui/templates.py` that would satisfy `check_mirror` does not exist and should not), but
the same filename is T025's (Phase 5, not this story) declared deliverable for the utility-class
allowlist and i18n guard.

**Chosen**: `tests/test_ui/__init__.py` created at T002, a one-line docstring; T004's own commit
does not recreate it. `tests/test_ui/test_templates.py` created at T003 holding only
`TestBaseTemplate`; `[tool.forge.conformance] non-mirror-paths` declares it there, as a one-entry
list. T025 extends both the file (a new `Test*` class) and the declared list (two more entries)
when it lands — it does not create either from scratch, and its own task text should be read with
that in mind.

**Why defensible**: both files are needed by an earlier task than the one that names them as its
own deliverable, and nothing about creating them early conflicts with what the naming task still
needs to do — T004 still adds `conftest.py` to an already-existing package; T025 still adds its two
guards to an already-existing module. Waiting would have meant either inventing a temporary empty
package/file only to fill it in later, or blocking T002/T003 on a task three-to-nineteen slots
ahead of them for no benefit.

**Revisit if**: T025's implementer finds the existing `test_templates.py` content or the existing
`non-mirror-paths` entry unexpected — this decision is exactly the context for why both are already
there.

**ADR:** none — a file-creation ordering note local to this run.

## D14 — The type-check plugin reads the core-only settings
**Ambiguity**: T005 unblocked the test job by installing the `ui` extra in CI, and the test matrix
went green. The Code Quality job then failed with `Error constructing plugin instance of
NewSemanalDjangoPlugin`. The two jobs are separate reusable workflows, and only the test one accepts
an install argument — the shared build workflow declares no `poetry-install-args` input at all, so
the extra cannot be passed to it from this repo.

**Chosen**: `[tool.django-stubs] django_settings_module` points at `tests.settings_core` rather than
`tests.settings`.

**Why defensible**: django-stubs calls `django.setup()`, so every app in the settings module's
`INSTALLED_APPS` has to be importable. `tests.settings` installs `literature.ui`, whose dependency
arrives through an optional extra that job does not install, so the plugin could not construct and
the whole job went red — including the parts that have nothing to do with this feature.

Nothing is lost by checking against the core-only settings. The plugin uses the settings module to
resolve model metadata, and `literature.ui` declares no models. django-mvp resolves to `Any` either
way: it ships no `py.typed`, and `ignore_missing_imports` is already set for the whole project.

The alternative was adding a `poetry-install-args` input to the shared build workflow and cutting a
release of it. That is the more general fix, since any package adopting an optional UI extra meets
this, but it is a change to another repository and a release cadence this feature does not own — and
it would still leave the type check depending on an optional dependency, which is the thing worth
avoiding. Pointing the plugin at the core settings makes the type check independent of the extra,
which is what it should have been.

**ADR:** none — a build-configuration choice local to this repo, with nothing downstream inheriting it.
## D15 — The credit row extends the catalogue row rather than restating it

**Ambiguity**: FR-034 requires a credit row on the contributor page to carry what a catalogue entry
carries. US-4 delivered that by copying `item_list_item.html` into `contributor_item.html` and adding
the roles line, which satisfies the requirement on the day and lets the two drift apart on any later
day.

**Chosen**: `contributor_item.html` extends `item_list_item.html` and fills one block with the roles
line. The catalogue row is defined once.

**Why defensible**: the requirement is that the two stay the same, so inheritance states it rather
than a convention restating it. Twenty duplicated lines went with it, and a change to what a
catalogue entry shows now reaches the contributor page by construction. Applied at convergence, with
the full suite green before and after.

**ADR:** none — one template extending another, inside this app.

## D16 — The reader-text guard ignores template comments

**Ambiguity**: the i18n guard (T021) flags any literal prose left in a shipped template outside
`{% translate %}`. It strips template tags, variables, HTML and entities, but not `{# … #}`
comments, so a comment explaining a template to the next contributor read as untranslated
reader-facing text.

**Chosen**: comments are stripped first, and a test proves prose inside one is not flagged.

**Why defensible**: the template engine never renders a comment, so there is no reader to translate
it for. The guard's own bar — "text a reader sees" — was what it failed to apply. Surfaced by the
convergence cleanup, which added the first comment to a shipped template.

**ADR:** none — a correction inside this feature's own test guard.

## D17 — The two tamper flags at convergence are accepted

**Ambiguity**: `forge tamper-check` flags `tests/settings.py` and `tests/urls.py` as pre-existing
test files this branch modified, which is the guardrail against a run weakening tests it cannot pass.

**Chosen**: both accepted.

**Why defensible**: neither is a test. `tests/settings.py` moved its whole body verbatim into the new
`tests/settings_core.py` and now imports from it before appending the UI stack, so the core-only
settings a core-only boot test needs exist as their own module; nothing was removed. `tests/urls.py`
gained the four-line mount the app is served from. No assertion was changed, relaxed or deleted
anywhere in the diff, and the file-by-file diff is in the pull request for confirmation.

**ADR:** none — a guardrail triage note for this run.

## D18 — The contributor page is a list view, not a detail view that paginates

**Ambiguity**: US-4 built the contributor page as an `MVPDetailView` of `Name` that assembled a
`Paginator` by hand and set `page_obj`, `grid_config`, `list_item_template` and `empty_state` into
the context itself, because a detail view does not mix in django-mvp's list machinery. Raised at the
merge gate: the view reproduced logic django-mvp already owns.

**Chosen**: `ContributorDetailView` subclasses `ItemListView`. The page is the catalogue filtered to
one contributor's credits, so pagination, page size, the empty state, the grid configuration and the
not-found on an out-of-range page all arrive with `MVPListView`. What remains is the part the base
class cannot know: the contributor is the page's subject, and each row carries the roles that
contributor held. `contributor_detail.html` is deleted; the page renders through `item_list.html`.

**Why defensible**: FR-036 requires the list to paginate and order exactly as the catalogue does.
Inheriting the catalogue view states that, where the hand-built version restated it and could drift
from it — the page size was already being read off `ItemListView` to stop exactly that. Around fifty
lines of view code and one template go with it, and every acceptance test for the page passes
unchanged, including the two-roles case, the past-the-end 404, the missing-contributor 404 and the
empty state.

**Cost named**: the counted line above the list now reads "Showing 1-3 of 3 references" rather than
"3 credited references", because the template is shared. No requirement names that wording.

**ADR:** none — a view composed from the app's own catalogue view, inside this app.

## D19 — The two page templates are recorded as stand-ins, not accepted as ours

**Ambiguity**: raised at the merge gate — `literature/ui/base.html` reproduces django-mvp's
`page_view.html`, and `item_list.html` reproduces the body of its `list_view.html`, so the app looks
like it is rewriting templates the dependency already ships.

**Chosen**: both stay, and both are now listed under the specification's *Component gaps* with the
upstream request that retires them (django-mvp#219).

**Why defensible**: the packaged chain is unreachable from a reusable app, not merely inconvenient.
`page_view.html` extends the unqualified `base.html`, which django-mvp does not ship — with mvp,
cotton, easy-icons and flex-menu all installed, `get_template("base.html")` raises
`TemplateDoesNotExist` while `get_template("mvp/base.html")` resolves. That name is the host
project's own file, so extending the chain would require every host to write one, which is exactly
what SC-002 forbids. Shipping a top-level `base.html` of our own would resolve project-wide and
displace the host's. `list_view.html` adds a second obstacle: it loads `crispy_forms_tags`, so it
needs `crispy_forms` in `INSTALLED_APPS` for a page carrying no form. Composing the frame from
django-mvp's own components is what its getting-started guide tells an app to do.

**Cost named**: about thirty lines that will drift from django-mvp when either template is improved
there. The exit is upstream and filed, not a promise to remember.

**ADR:** none — a temporary stand-in tracked in the specification, with a filed exit.
