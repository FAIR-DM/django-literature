# Decisions — 011 Import a bibliography file through the front end

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without escalating. The
spec stands alone; this file explains why it says what it says.

## D1 — The reader always lands on a report, never on the catalogue with a message

**Ambiguous:** the issue's closing sentence offers two landings — a report page, or a redirect back
to the catalogue carrying a message summarising the import.

**Chosen:** always the report page.

**Why defensible:** the same issue's preceding sentence rules the redirect out. "Rather than
guessing from a count" is a requirement that the reader be able to see which entries failed and
why, and a flash message on the catalogue is a count. The two sentences only look like a choice
because the second one lists the shapes a response can take; read against the first, the redirect
is not an acceptable variant of the requirement, it is the outcome the requirement exists to
prevent. Confirmed with Sam at intake.

A conditional redirect — report on failures, redirect on a clean run — was the obvious middle and
was rejected too. It makes the interface's behaviour depend on the data, so a reader who has only
ever imported clean files never learns the report exists, and the first time they meet it is the
first time something went wrong. It also gives the demo's guard two paths to walk instead of one.

## D2 — Nothing about the run is stored

**Ambiguous:** whether the report is a rendering that exists once, or a stored import record the
reader can return to.

**Chosen:** it exists once. No model, no table, no history.

**Why defensible:** an import record is a different feature with its own requirements that nobody
has stated — who may see whose imports, how long they are kept, whether the file itself is kept,
what happens to a record whose references were later deleted. Every one of those is a decision, and
adding a model to this feature would take all of them silently and by default. The issue asks for
the reader to see what became of every entry, which the response satisfies.

The cost is real and worth naming: a reader who navigates away loses the report, and re-running the
import to see it again creates the references a second time, because nothing is de-duplicated
(D5). That is why the report is one page rather than paginated (D4) and why the import page warns
about repeat imports before the reader submits.

If an import history is wanted later it arrives as its own issue, and it can be built without
disturbing anything here — the contract already returns the whole result, so storing it is additive.

## D3 — The report counts entries from one, the contract counts from zero

**Ambiguous:** the import contract identifies every entry result by a zero-based index, deliberately
and for good reason. The report shows entries to a person.

**Chosen:** the report numbers the first entry as one. The contract keeps its zero-based index
unchanged.

**Why defensible:** these are two different jobs. The contract's index is an identifier in a
returned data structure, where zero-based is the convention of the language it is returned in and
matches the position in the list it is returned as. The report's number is a counting word offered
to a reader who is looking at their own file: nobody scrolling a `.bib` export calls the first entry
"entry zero". Aligning them would mean either making the code awkward or making the interface wrong.

This is written down because it is exactly the kind of inconsistency a later reader will find and
"fix" in one direction or the other, restoring the problem. Neither number is a mistake. The
divergence is the decision.

## D4 — The report is one page, however long the file was

**Ambiguous:** a four-hundred-entry file produces a four-hundred-row report, which in any other
listing in this package would be paginated.

**Chosen:** no pagination.

**Why defensible:** pagination assumes the pages can be returned to. This report cannot be — it is
not stored (D2), so a second page would have to be reachable only from the first, in one session,
and a reader who reloaded or navigated would lose all of it including the part they had already
read. A long single page is honest about what the report is. It also keeps the thing a reader
most needs, the failed entries, reachable by searching the page in their browser rather than by
walking pages hunting for them.

## D5 — No duplicate detection, and the import page says so

**Ambiguous:** a reader importing a file they have imported before gets the references twice, and
the interface is the first place anyone would expect that to be caught.

**Chosen:** it is not caught. The import page states plainly, before the reader submits, that a
repeated import creates the references again.

**Why defensible:** the package has settled this twice and refused both times — ADR 0009 states
that no import compares an incoming entry against anything already stored, and ADR 0023 removed
even the batch-scoped collision handling that survived the first decision. `Item.citation_key` is
indexed and deliberately not unique. Acquiring detection in the front end would mean the same file
imported from the interface behaved differently from the same file imported from code, which is a
worse outcome than either behaviour on its own, and it would do it without the decision ever being
taken.

Warning is not detection and costs nothing. It converts a surprise into an informed action, which
is the whole of what the front end can honestly offer here.

## D6 — The format is chosen, never sniffed

**Ambiguous:** the front end could detect the format from the file's extension or its first bytes
rather than asking.

**Chosen:** the reader chooses. The front end does not look at the file.

**Why defensible:** Sam specified the choice at intake, and the reasons hold independently.
Detection is a guess that fails silently in the one case that matters: a file whose extension or
opening lines suggest one format while its body is another gets imported as the wrong thing, and
what comes back is entries reported as created and quietly wrong. Spec 004 made the same argument
when it refused to read BibLaTeX as classic BibTeX, and reached the same conclusion — a refusal a
reader can act on beats a silent misreading.

When the choice is wrong, the format itself says so in words already written for that purpose
("No BibTeX entries found. Is this a BibTeX file?"), reported through the ordinary report rather
than as an error. So the mismatched case is already handled, by the layer that knows.

The choices offered are read from the installation's configured formats rather than listed in the
front end, so a project that adds a format gets it in the interface for free and this feature never
has to be revisited to add one.

## D7 — Both catalogue presentations carry the action

**Ambiguous:** Sam named the table's toolbar. The package serves two catalogue presentations — the
table by default, and a card list a project can route to instead.

**Chosen:** both, from one definition of the action.

**Why defensible:** FS-010 settled this exact fork for search and filtering, and the reasoning
transfers without modification: a project that chooses the card presentation must not silently lose
a capability, or a documented routing choice becomes a trap. Giving the import to the table alone
would mean a project reading the routing setting had no way to know it was also giving up importing.

Naming the table rather than both is how the entry point was described, not a boundary that was
drawn — the table is what the package serves by default, so it is what "the catalogue" means in
conversation. Raised in the specification gate brief so it can be vetoed if that reading is wrong.

## D8 — The front end reads the contract and does not extend it

**Ambiguous:** whether anything the report needs is missing from what the import contract returns.

**Chosen:** nothing is. The feature adds no reading path, changes no converter, and ships no
migration.

**Why defensible:** the contract was written to be exactly this — spec 003 settled the shared import
surface before any format existed, so that adding a format was a mapping exercise rather than a new
public API, and it fixed per-entry outcome reporting as the point of the whole thing. The result
carries an outcome, a position, a handle where the syntax offers one, a reason on every failure, and
the created object. That is the report's every column.

Spec 005 set the precedent for what happens if that turns out to be wrong: RIS was positioned as the
proof of the contract, with the rule that a format unable to ship without changing the contract
raises a finding as its own issue rather than amending in place. The same rule applies here, and it
is written into the spec's assumptions so that whoever meets a genuine gap raises it rather than
widening this feature to cover it.

## D9 — Permissions are not introduced, and that is flagged rather than assumed

**Ambiguous:** import is the most consequential write the front end offers, and nothing in the front
end checks permissions.

**Chosen:** no permission checks, matching FS-008 for creating, editing and deleting references —
but stated in the spec rather than left implicit, and raised in the gate brief.

**Why defensible:** the precedent is unambiguous and recent. FS-008 shipped create, edit and delete
with no permission model, FS-009 and FS-010 left it alone, and a package that gates one write path
and not the others is more confusing than one that gates none — a host reading the code would
reasonably conclude the ungated paths were an oversight. Access control for the front end is a
feature in its own right, and taking it here, for one view, would prejudge how it works everywhere
else.

What makes this worth a decision rather than a silent inheritance is the size of the difference. A
create form adds one reference at a time; an import adds a file's worth, and a reader who reaches
the page can fill a catalogue in one action. If Sam wants the front end gated, this is the feature
where the cost of not having it is highest, so the gate brief names it as a veto point.

## D10 — The two formats are made to agree on what a file handle is, before any front-end work

**Ambiguous:** the import contract documents `import_file`'s argument as "an open file object, or
anything with a `read()`". Planning established that the two shipped formats mean different things
by it, and that a browser upload satisfies only one of them.

**Chosen:** both formats accept either a text or a binary handle, decoding bytes themselves. It is
the first task in the run, ahead of everything front-end.

**Why defensible:** the measurements are in `research.md` R1 and they are unambiguous — BibTeX
requires text and fails on bytes with `TypeError: cannot use a string pattern on a bytes-like
object`; RIS requires bytes and fails on text with `AttributeError: 'str' object has no attribute
'decode'`. Neither raises to the caller, because the runner catches everything, so each arrives as a
report of one failed entry whose reason names a Python type error. Django hands a view bytes,
always. So without this fix the feature ships a BibTeX path that fails every file with a reason the
reader cannot act on, which is precisely the outcome the report exists to prevent.

The alternative — the view decoding for BibTeX and not for RIS — was rejected on three counts. It
contradicts ADR 0012, which puts decoding with the format on the grounds that only the format knows
its own encoding conventions. It contradicts FR-010, which keeps any reading path out of the front
end. And it breaks for any third format a project configures, which FR-005 explicitly supports; the
front end would be carrying a table of handle types it cannot possibly keep current.

The spec forbids changing the import contract, any model or any converter (FR-028). A format's
`parse` is none of the three, and what changes is not the contract's shape but a documented input
type that two implementations already disagreed about. The change is additive in both directions:
every existing caller keeps working, because each format continues to accept what its own tests
already pass it.

RIS is the one that was right. It owns its decoding and raises a `ParseError` a reader can act on
when the bytes are not decodable. BibTeX gains the same step, with the same error, which is why
this reads as bringing one format up to the other rather than as a new behaviour.

Raised on the tracker in its own right, so the defect has a record that does not depend on anyone
reading this feature's specification.

## D11 — FR-023 is narrowed to the guarantee that can be kept

**Ambiguous:** the specification required that reloading the report not re-run the import. Planning
established that this cannot hold at the same time as FR-031, which stores nothing about the run.

**Chosen:** the report is rendered on the response to the upload. FR-023 now says that one
submission imports the file once and that the report page carries no control that runs it again.

**Why defensible:** the wider guarantee needs the result to survive between two requests, so that
the upload can redirect to a report fetched with an ordinary GET. That means the session. A report
of several hundred entries does not fit a signed-cookie session, so the package would be requiring
its host to run a database or cache session backend — and Article X says a host adopting this
package makes no structural changes to accommodate it. A reusable app does not get to impose that.

What is left is what every server-rendered upload in Django does, including Django's own admin: the
result renders on the POST response, and a reader who reloads meets the browser's resubmission
prompt. The prompt is the browser's, it is familiar, and it asks before doing anything.

This is a criterion written at specification time that implementation reality narrowed before any
code existed, which is what the planning stage is for. It changes no scope, so it does not go back
through the specification gate; it is raised in the plan notification instead, where Sam can object
at no cost.

If an import history is built later (D2), the redirect becomes available for free, because the
result would then have somewhere to live that is not the session.

## D12 — The unauthenticated, unbounded upload is accepted and written down

**Ambiguous:** nothing, in the sense of a choice left open — but this feature opens the project's
first file-upload boundary, and the specification approved both halves of what that means without
naming the combination.

**Chosen:** no change to the design. The two assumptions stand as approved: nothing in the front end
checks permissions, so the import page is reachable by whoever can reach the catalogue, and the
package imposes no size limit of its own on the submitted file. FR-007 additionally forbids the
front end inspecting the file, so an extension or content-type allowlist is ruled out by
requirement, not by choice. What changes is that the documentation says so plainly rather than
leaving a reader to infer it.

**Why defensible:** the endpoint grants no privilege the already-open create page does not. What it
adds is throughput — one anonymous request now parses a caller-sized file in the worker and can
create thousands of references and their related rows, where the create page makes one. That is a
real difference in kind of exposure, and it is the host project's own upload size, request timeout
and access rules that bound it, because a reusable app cannot bound them for its host without
imposing the structural assumptions Article X rules out.

Recorded rather than fixed, because both halves are approved specification text. Changing either
means amending the specification and putting it back to the maintainer, not something planning may
take on its own.

## D13 — `RISParser`'s own docstring is amended in place, superseding spec 005's D19

**Decision:** `RISParser.parse`'s class docstring, which stated "Expects `file` opened in
**binary** mode" and cited spec 005's `decisions.md` D19 for why, is rewritten in place (T004) to
say what T004 actually implements: either mode is accepted, a binary read is decoded here as
before, and a text read passes through unchanged. It now names D10 as superseding D19 rather than
silently disagreeing with it.

**Why:** D19 is a real, still-true record of spec 005's own reasoning — RIS's decoding needs the
raw bytes to name an encoding and a byte offset on failure, which is exactly what T004 preserves
for the binary path. Leaving the docstring as "expects binary" after T004 lands would make the one
piece of documentation next to the code actively wrong, which is worse than the stale-but-harmless
module comment elsewhere in `ris.py` claiming "no RIS-to-CSL mapping yet" (unrelated to this task
and out of this phase's scope to fix). D19 itself is not edited — it lives in a different spec's
`decisions.md`, outside this phase's file scope (prohibitions), and it is not wrong about what it
records; it is superseded by a later decision, which is a fact this phase's own D10 already states
in prose. This entry is what makes that supersession discoverable from the code side, not just the
spec-011 side.

**Revisit if:** a third format is added whose own decoding failure needs something a text handle
cannot supply — at that point the "text read passes through unchanged" half of D10 may need its
own carve-out, and D19's original reasoning is the place to start.

## D14 — "import" is taught to `get_url_kwargs()` as a collection-level action

**Ambiguous:** research.md R2 and the plan both settle on carrying the import URL through
`CRUD_VIEWS` / `directory` / `show_import_action` — django-mvp's own mechanism — but neither names
what `CRUDDirectoryMixin.get_url_kwargs()` actually does with an action it does not recognise.

**Chosen:** `ItemListView` and `ItemTableView` each override `get_url_kwargs()` to return `{}` for
`"import"`, the same as the base class already does for `"list"` and `"create"`.

**Why defensible:** measured directly against the installed package
(`CRUDDirectoryMixin.get_url_kwargs()`, `mvp/views/detail.py`): `if action in {"list", "create"}:
return {}` — anything else falls through to `dict(self.kwargs) or None`. On a list view `self.kwargs`
is always `{}` (no URL captures the route needs), so `dict({}) or None` is `None`, and
`resolve_crud_url("import")` returns `None` before it ever reverses anything. Without this override
`directory.import_url` never resolves and the toolbar action's `{% if directory.import_url %}` never
renders — not a cosmetic gap, the whole seam this feature adds. The override is the narrowest fix:
one `if`, delegating everything else to `super()`, on the two views that show the action — never on
`CatalogueListMixin`, which the contributor page also composes and must not gain either the action
or the URL (hazards, T114).

The one test this forces a second look at is `tests/test_ui/test_urls.py`'s own
`TestCRUDViewsReverse::test_every_action_the_view_shows_reverses`, which mirrors the same
"collection-level actions take no pk" rule as a hardcoded `{"list", "create"}` set, independently of
`get_url_kwargs()`. That set gains `"import"` too, in the same commit as this decision — not a
weakened assertion (it still reverses every shown action with the right kwargs), a corrected mirror
of a rule that genuinely has a third member now. Flagged in the completion report's `deviations`
rather than silently folded in, since the brief names only one shipped test as sanctioned to edit.

**Revisit if:** a future action joins `directory` that is genuinely object-level but not yet routed
under a `pk` — the two-branch shape here (`{}` vs `dict(self.kwargs) or None`) would need a third
case rather than a second hardcoded name.

