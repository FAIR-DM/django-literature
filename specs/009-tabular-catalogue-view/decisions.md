# Decisions — 009 A tabular catalogue view

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without escalating. The
spec stands alone; this file explains why it says what it says.

## D1 — The title chain ends at the citation key, duplicating a column

**Ambiguous:** intake settled that the title column is a fallback chain rather than a composed
cell. It did not say which of the ten title fields are in the chain, in what order, or what a cell
shows when a reference carries none of them.

**Chosen:** the reference's own `title`, then `title_short`, then `original_title`, then
`volume_title`, then `citation_key`. A cell that reaches the end of the chain shows the citation
key, which is also the row's first column.

**Why defensible:** the chain runs from the most specific statement of what the thing is called to
the least, and stops before the fields that name something other than the item itself.
`container_title`, `collection_title` and `part_title` name the thing the reference sits inside,
not the reference; `reviewed_title` names a different work altogether. Putting any of them in the
chain would print a journal's name in the title column of an article that happens to have lost its
own title, which is worse than an honest fallback.

The duplication at the end is deliberate and is the lesser of two faults. The title cell is what
links to the reference — that is the convention the card already sets, and the one every reference
manager follows — so the cell can never be allowed to render as an empty-value marker: a link whose
visible text is a dash is not something a reader can read, click with confidence, or reach by
keyboard with any idea of where it goes. The card already does exactly this, falling back from
`title` to `citation_key` in one step, so the chain extends established behaviour rather than
inventing one. The case is rare — a reference with no title of any kind is a badly-formed import —
and when it happens the row reads as the same handle twice, which is legible, rather than as a
row that cannot be opened.

## D2 — Contributor names in a cell stay linked

**Ambiguous:** whether the authors column carries plain text or the links the card carries.

**Chosen:** each name links to that contributor's page, as on the card.

**Why defensible:** FS-006 US-4 made a contributor's page a deliverable, and the catalogue list is
where a reader gets to one. Serving the table by default while dropping the links would withdraw a
reachability guarantee an earlier feature established, in the same release, without saying so. The
demo's guard reaches a contributor page by following links rather than by constructing an address,
so the withdrawal would surface as a broken walk rather than as a decision anyone took.

## D3 — Three names, then a translatable indication of more

**Ambiguous:** a row is one line by default and a reference may credit dozens of contributors.

**Chosen:** the first three credited names in stored order, then a translatable string stating that
more are credited.

**Why defensible:** the alternatives are worse in both directions. An unbounded list either makes
one row as tall as the page or is clipped by the browser mid-name, and where it clips depends on
the column width, so the same catalogue reads differently on two screens. A single name loses the
distinction between a sole-authored paper and a collaboration, which is information a reader scans
for. Three is what reference managers settle on and is enough to recognise a paper by its team.

The indication is a translated string rather than the Latin *et al.* set in the template: Article
VIII is non-negotiable and a hard-coded user-visible string is a blocking review comment. A locale
that does not use the Latin abbreviation gets its own wording.

## D4 — Two columns declare themselves unsortable rather than sorting on something else

**Ambiguous:** intake settled that headers sort. It did not say which of the seven columns do.

**Chosen:** citation key, item type, title, container title and issued date sort. Authors and the
edit control do not.

**Why defensible:** the authors cell is assembled from `ItemName` rows across two roles, with a
fallback between them, and truncated at three. There is no single stored value it corresponds to,
so any ordering offered on it would be ordering by something the reader cannot see — most likely
the first contributor's family name, which is not what the cell shows for a reference credited to
editors, and not what it shows at all when the fallback fires. A heading that offers a sort and
then reorders by an invisible key is a worse outcome than a heading that offers none, because the
reader has no way to discover the discrepancy. The edit column holds a control rather than data.

The title column is the borderline case and is included. It sorts on `title`, which is what the
cell shows for every reference that has one; the divergence is confined to the same rare
badly-formed references D1 covers, where the cell is showing a fallback. That is a narrow and
explicable divergence rather than a systematic one.

## D5 — Item type sorts by the stored value, and the docs say so

**Ambiguous:** whether sorting by item type follows the reader's alphabet or the store's.

**Chosen:** the stored CSL type value. The documentation states it.

**Why defensible:** the displayed label is translated, so ordering by it would produce a different
catalogue order in each language and could not be done in the database in any case — it would mean
pulling every row into memory to sort it, which contradicts FR-012 and stops being viable at
exactly the catalogue size a table exists to serve. The stored order is stable, and CSL's type
names are close enough to their English labels that the result reads as alphabetical to an English
reader. Saying so in the documentation is what turns a surprise into a documented behaviour.

## D6 — The search and filter controls are switched off explicitly

**Ambiguous:** the table view arrives with search, filter and create among its default controls,
and this feature ships only create.

**Chosen:** the excluded controls are named and switched off, not left to whatever the underlying
default happens to be.

**Why defensible:** this is the pattern the current catalogue already follows — `ItemListView` sets
`search_fields = None` and `order_by = None` explicitly, with a comment naming #49 as the owner, so
that a later change to a default cannot resurrect a control the feature excluded. The reasoning
carries over unchanged: an upstream release that adds a control to the default set would otherwise
put an unspecified, untested, unfinished search box on the package's default page.

## D7 — Nothing is deprecated when the default changes

**Ambiguous:** what "becomes the package default" means for a project already serving the card
list.

**Chosen:** the documented catalogue route serves the table after upgrading. The card view stays
public, documented and used — the contributor page goes on rendering cards — and a project that
wants the previous page changes one line of routing.

**Why defensible:** Article X makes this a package embedded in someone else's project, and the
front end's routing is theirs to own: URL patterns are optional and namespaced, and a host includes
them at a prefix it chooses. That is what makes a change of default recoverable in one line rather
than a fork. Deprecating the card view would say the opposite of what issue #81 asks for, and the
contributor page keeps a live user inside the package, so the card path stays exercised by the
suite rather than surviving only as a documented promise nobody runs.

## D8 — The stack constraint on front-end packages is lifted, on this branch

**The situation:** the constitution's stack constraints named django-mvp as the one adopted UI
layer and said in terms that "no further third-party form/table/filter/JS package is prescribed;
adopting another is a constitutional amendment". Governance then said amendments are never made
mid-feature. Adding the table package this feature needs therefore required a second pull request
before this one could proceed.

**Chosen:** the restriction is removed rather than satisfied. Front-end additions to the `ui`
extra now sit under Article VII's ordinary dependency discipline — a stated justification,
`deptry` clean — keeping the two conditions that were doing the real work: the core never gains a
front-end dependency, and django-mvp's own integration is the route in where one exists. The
amendment is carried on this branch, with the constitution moving to 4.0.0, and is declared in the
pull request's description.

**Why defensible:** the bar was heavier than the decision it governed. The package being added is
one the adopted UI layer already integrates with and is only reachable through that integration,
so admitting it changes nothing about what governs the interface — it is the mechanism django-mvp
prescribes for exactly this, not a competing way to do something django-mvp already does. Routing
that through a constitutional amendment made the constitution the bottleneck for every interface
feature, and a rule paid mostly in process is a rule that gets worked around rather than followed.

The governance clause changed with it, from a prohibition to a disclosure rule. What the
prohibition protected against is a branch quietly widening a rule it is judged against, and
requiring the amendment to be declared in the pull request's description addresses that directly.
The prohibition instead forced a separate pull request carrying one paragraph, which buys the same
protection at the cost of a second review cycle.

**Whose call:** Sam's, made explicitly at spec sign-off ("Remove that constraint from the
constitution with this PR. That is too restrictive."). The governance clause amendment is the part
resolved here rather than asked: leaving it in place while amending under it would have made the
change self-contradicting on its own terms.

## D9 — Presentation only: no model, no field, no migration

**Ambiguous:** whether any column needs something the store does not hold.

**Chosen:** none does.

**Why defensible:** checked column by column. Citation key, title, short title, original title,
volume title and container title are scalar fields on `Item`. Item type is `Item.type` against
`ItemType`. The credited names are `ItemName` rows carrying role and position, which Article XI
already requires stay relational and queryable. The issued date is the `ItemDate` occupying the
`issued` slot, at most one per reference by construction. Ordering by issued date reads that
related row rather than a denormalized copy, so no field is added to make a sort cheap.

## D10 — The foundational phase was implemented directly, not dispatched

Three mechanical tasks — a dependency bump, a lock regeneration, and one settings entry in two
files — with no design content between them. Dispatching them into a worktree would have cost more
than it saved, and the plan's design decisions were already settled. Recorded here because skipping
dispatch is the exception, not the default.

## D11 — The app's pass-through `base.html` was deleted, not carried forward

Not a decision so much as an instruction coming due. The file existed because django-mvp routed
every packaged page through an unqualified `base.html` and shipped no default, so an installable app
could not reach the packaged chain in a project that had written none. Its own comment named the
condition for its removal: "It is deleted the moment django-mvp ships a default of its own
(django-mvp#219)."

That issue closed on 2026-08-12 and the default shipped in django-mvp 0.18. Raising the floor to
0.19 for the table layout therefore also satisfied the pass-through's deletion condition, and the
suite said so immediately — a template test failed because django-mvp's own `base.html` now wins
the lookup.

The file is gone. Its tests are not: what they guaranteed was that the packaged chain resolves for a
project with no `base.html` of its own, and that a project which has one still wins. Both are still
asserted, now against django-mvp's default rather than ours. The floor this package declares is what
guarantees the replacement is present.

## D12 — `deptry` is red between declaring django-tables2 and importing it

The foundational phase declares the dependency; the first module that imports it arrives with the
first story. In between, `deptry` reports DEP002 — declared but unused — which is correct and
temporary. It is left red rather than silenced with an ignore entry that would have to be found and
removed a day later. The story's exit gate is where it must be green.
