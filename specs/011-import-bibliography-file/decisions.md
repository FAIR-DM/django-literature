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

## D15 — The fixture's failing entry fails on an oversized `address`, not an unmapped type

**Ambiguous:** T301 asks for "at least one [entry] that does not" convert, without saying what
should make it fail. Several shapes were available: an unrecognised BibTeX entry type, a malformed
identifier, an unresolvable date.

**Chosen:** the failing entry (`ImportFixtureGamma2022`) is a well-formed `@article` whose `address`
field is 331 characters — over `Item.publisher_place`'s 255-character limit (`literature/models.py`).

**Why defensible:** every other shape recovers rather than fails. An unrecognised entry type maps to
the CSL `document` fallback (`ENTRY_TYPE_TABLE`, `bibtex.py`) rather than failing the entry; a
malformed DOI or ISBN is preserved under `custom` rather than raising (`bibtex.py`
`to_csl_json`'s identifier branch); an unparseable date falls to CSL's `literal` slot. The only path
that reaches `EntryResult.FAILED` for BibTeX is `Item.full_clean()` raising inside
`from_csl_json` (`literature/importers/base.py::import_entry`) — a value that maps cleanly to a
Django field but does not fit it. `address` (→ `publisher-place` → `Item.publisher_place`,
`max_length=255`) is a plain scalar field with no cleaning step of its own, so an oversized value
is the shortest path to a real, uncontrived failure: something a real `.bib` export could plausibly
carry (a full institutional address line) and something the importer cannot recover from, reported
as `"Ensure this value has at most 255 characters (it has 331)."` — a reason a reader can act on,
which is what `walk_import` (T304) asserts against.

Confirmed by running the fixture through `BibTeXFormat().import_file()` directly against a migrated
test database before writing `walk_import`: two entries `CREATED`, the leading `%`-comment header
`SKIPPED` (bibtexparser's own handling of text outside any entry, harmless to the report), and
`ImportFixtureGamma2022` `FAILED` with exactly that reason.

**Revisit if:** a future importer contract adds field-level cleaning for every scalar (not only
identifiers), at which point an oversized `address` might also start recovering rather than failing,
and the fixture would need a different failure shape.

## D16 — Importing previews by default, and the staged file lives on disk

**Ambiguous:** nothing, at specification time. FR-030 forbade a preview and FR-031 stored nothing.
Sam reversed both after using the shipped pages, on the grounds that a report which arrives after
the fact cannot change anything.

**Chosen:** submitting the form runs a dry run and reports it as a preview; a control on that page
carries out the import it described. A checkbox on the form skips the preview. The submitted file is
staged on disk between the two requests.

**Why defensible:** the report is the feature. Its whole value is telling a reader what a file did to
their catalogue, and a reader who can only learn that afterwards is left undoing it by hand — with no
duplicate detection (D5) to help them, because a re-import after a bad one doubles the damage. The
importer already supports exactly this: a dry run runs every stage and reports identically inside a
transaction that is rolled back, and it was built at the same time as the contract for this purpose.
The front end was declining to use a capability the core already had.

The cost is that FR-031 no longer holds literally. A file has to survive between the preview and the
confirmation, because a browser will not re-populate a file input and asking a reader to re-attach a
file to confirm it defeats the point of previewing. This is staging, not a record: it is one file, it
is removed when the import it was staged for is carried out, and abandoned ones are swept. No history
of imports is kept and D2 stands unchanged.

django-import-export solves the same problem the same way, and reading its implementation is what
settled the design. Three things in it are not copied and are the reason this is worth writing down:

- **The staged file's identity lives in the session, not in the page.** Its confirm form posts the
  temp filename back as a hidden field, and `process_import` checks only that the requester has import
  permission — which returns true for any admin user unless a setting is configured. Anyone holding a
  name can confirm someone else's staged upload. Here the name is never in the page at all, so a
  request can only confirm what its own session staged. That is FR-042, and it costs nothing.
- **The format is carried with the staged file, not re-read from the confirmation.** Theirs takes the
  format and resource from the confirming POST, so what commits is not guaranteed to be what was
  previewed.
- **Abandoned stagings are swept.** Their `remove()` is called in one place and not in a `finally`, so
  a preview that errors, or that the reader walks away from, leaves the file behind indefinitely.

Their exposure is bounded by the admin being staff-only. Ours would not be — this front end has no
permission model at all (D9) — so the same design without those three changes would be worse here
than it is there.

## D17 — What the report looks like, settled by use rather than by specification

**Ambiguous:** the specification said what the report must contain and left its presentation open.
Reading a real one showed the difference.

**Chosen:** outcomes render as colour-coded badges. The way back to the catalogue is a button with a
backward arrow, beside a second button that returns to an empty form. The form sits above the results
on the report page, divided from them, so another file can be submitted without navigating away. Where
the file could not be read at all, the submit control reads *Retry* and stays disabled until the
attached file changes.

**Why defensible:** these are Sam's, from using the pages, and that is the right source for them — a
specification can require that failures be distinguishable (FR-019) without being able to say what
makes them so on a screen. The one with reasoning worth keeping is the disabled Retry: re-submitting a
file the format could not read produces the identical failure, so a control that invites it is
inviting a wasted round trip. Requiring the attachment to change before the control activates makes the
page say what the reader has to do differently.

Keeping the form on the report page also removes the tension D11 recorded. FR-023's second half — that
the report carry no control re-running the import — was the best available answer when the report was a
dead end. It now carries one deliberately, and the preview is what makes running it again safe.

## D18 — A skipped entry may carry a reason

**Ambiguous:** the import contract sets a reason if and only if an entry failed, and actively raises if
a skipped entry carries one. So a format that knows exactly why it skipped something has nowhere to
put it, and the report shows a row with no key and no explanation.

**Chosen:** a skipped entry may carry a reason, and both shipped formats supply one. A created entry
still may not.

**Why defensible:** the contract's rule was a reasonable reading of "a reason explains a problem", and
using it showed the reading was too narrow. Skipping is not a failure but it is still something the
reader did not ask for, and every skip in the package has a specific, nameable cause the format
already knows: a comment or preamble block, header material before the first record, a fragment
carrying no type. Withholding it produces a row that a reader cannot act on or even interpret, which
is the outcome the whole feature exists to prevent.

This changes the import contract, which FR-028 forbade, so FR-028 is amended rather than worked
around. The change is additive: a reason on a skipped entry is a field that was previously always
absent, no existing caller can be reading it, and the invariant that a created entry carries none is
untouched. Raised on the tracker in its own right so the contract change has a record that does not
depend on anyone reading this feature's specification.

The alternative — the front end supplying its own words for a skipped row — was rejected outright. It
would mean the interface inventing an explanation the importer never gave, which is worse than saying
nothing.

## D19 — The staging retention window is a judgement call, recorded rather than derived

**Ambiguous:** FR-043 requires that a staged file left behind by an unconfirmed preview eventually be
swept, but names no figure for how long it may sit first.

**Chosen:** 24 hours, as `literature/ui/staging.py`'s `RETENTION_WINDOW` module constant.

**Why defensible:** no requirement or clarification session settled a number, so this is implementation
judgement rather than a reading of the spec, and is recorded here per `craft-increments` rather than
left as an unexplained constant. A day is long enough that a reader who previews a file and is
interrupted — a phone call, the end of a shift — can still come back and confirm it before it is gone,
and short enough that the unauthenticated, unbounded upload endpoint D12 already accepts does not
accumulate staged files on disk indefinitely between sweeps, which only run on entry to the import view
(T507).

**Revisit if:** a host reports either edge in practice — staged files disappearing before a reader
returns to confirm them, or disk use from abandoned previews becoming a real cost — at which point the
figure itself is what to change, not the mechanism.

## D20 — Four shipped tests are brought onto the refined default, with reasoning

**Ambiguous:** nothing in the specification. Four tests written for the original design assert what
FR-038 makes false by construction: three that a plain submission writes to the catalogue
(`TestItemImportView`'s BibTeX, created-row-link and mixed-file cases) and one that the report page
carries no form (`TestImportReportPage`). No implementation of the refinement can satisfy them.

**Chosen:** the three view tests now tick the skip-preview control, so they exercise the path that
still imports in one step and keep asserting what a real import does to the catalogue. The
report-page tests do the same, so the class reads a report rather than a preview. The no-form
assertion is replaced by one that the page is not a preview.

**Why defensible:** the guardrail on editing a shipped test exists because a failing test is usually
evidence about intent that the code is contradicting. Here the intent is what changed, and it changed
at a gate: FR-030 was reversed and FR-023's second half retired (D16, D17), both recorded in
`spec.md` before any of this phase's code was written. The tests are not weakened — every assertion
they made is still made, against the path that still behaves that way — and the behaviour they used
to cover as the default is covered as the default by `TestItemImportPreview`, `TestItemImportConfirm`
and `TestItemImportSkipPreview`. The phase that wrote the refinement was not sanctioned to touch
them and correctly stopped and reported instead; the edit is made here, deliberately and with this
record, rather than inside the phase that had the motive to make them pass.

## D21 — A pre-existing test in test_base.py is left red by ADR-0027, and reported rather than fixed

**Ambiguous:** nothing in this phase's own brief, whose hazards name exactly one shipped test as
sanctioned to edit (`test_results.py::TestEntryResult::test_reason_belongs_only_to_failure`) and say
of any other: stop and report it, do not edit it.
`tests/test_importers/test_base.py::TestReporting::test_skipped_is_distinguishable_from_failed`
constructs `SkipEntry("a comment")` through the generic test double `make_echo_format` and asserts
`result.skipped[0].reason is None`. ADR-0027 carries a `SkipEntry`'s message onto the skipped entry's
reason in exactly the code path (`BibFormat.import_entry`'s conversion-stage handling) this test
exercises, so the assertion is now false: the reason reads `"a comment"`.

There is no way to carry a format's `SkipEntry` message through that shared runner method without
also carrying this test double's — the runner does not, and should not, distinguish a real format
from a test one. Widening `import_entries`'s separate reader-stage handling (the one path that could
have been left untouched) would not have helped: this test's `"skip"` kind raises from `to_csl_json`,
not from `parse`, and neither shipped format raises `SkipEntry` from `parse` at all.

**Chosen:** report the failure, its cause and its file and line, without editing it. The same
guardrail D20 records — a failing pre-existing test is evidence about intent the code may be
contradicting — applies here, and this phase's own brief withheld authorization to resolve it.

**Why defensible:** the same reasoning D20 gives for why an edit *can* be correct also gives the
condition under which it is not this phase's to make: the intent genuinely changed, at a decision
recorded before this phase touched any code (ADR-0027, issue #107) — but the phase that discovers a
casualty of a sanctioned change is not automatically the phase authorized to adjudicate it, and this
one's brief said so explicitly. `test_skipped_is_distinguishable_from_failed`'s own assertion is not
wrong about what it once verified — a skip never carrying a reason — it is only wrong about the
contract now, and updating a test to match a contract it predates is exactly the kind of correction
that wants a record and a reviewer with the authority this phase was not given.

**Revisit when:** whoever reviews this phase either grants the edit (bringing the test's assertion
onto the amended contract, the same move D20 already made once) or decides the reader-stage path
should carry a reason too, in which case the fix travels together with this test's update.

## D22 — D21 resolved: both stages carry a skip's reason, and the pre-existing test is brought onto the amended contract

**Ambiguous:** D21's own two-way question, left open for review.

**Chosen:** both of its branches, because they turned out to be the same answer.

`import_entries`'s reader-stage handler now carries a `SkipEntry`'s message through `_skip_reason`,
exactly as `import_entry`'s conversion-stage handler does, and the existing test covering that path
(`test_skipentry_from_the_reader_is_a_skip_not_an_escape`, which already supplied the message
`"trailing junk"`) now asserts it arrives. `test_skipped_is_distinguishable_from_failed`'s final
assertion moves from `reason is None` to the reason its own double supplies.

**Why defensible:** an asymmetry between the two stages is not a smaller change than removing it —
it is a permanent one. It would mean the contract answering "may a skipped entry name what was
skipped?" with "depends which stage recognised it", a distinction the report cannot show and a
reader has no way to interpret. Nothing in the amendment Sam approved draws that line: #107 is about
a skipped row being readable, and where in the runner the format raised is an implementation detail
of the format. The one-line widening removes a documented deviation instead of adding one.

The test edit is the move D20 already made and D21 correctly declined to make unilaterally. Its
assertion was true about the contract that preceded ADR-0027 and is false about the amended one;
the test's stated purpose — FR-011, a recognised non-record is not reported as an error — is carried
by its other four assertions, all untouched, and the invariant that a created entry carries no
reason is still asserted in `test_results.py`.

**Verified:** the full suite is green at 1,813 tests, including both edited tests and the widened
reader-stage assertion.

## D23 — Two pre-existing tests in test_views.py are left red by the Phase 7 refinement, reported rather than fixed

**Ambiguous:** nothing in Phase 7's own brief, whose prohibitions name the same rule D20/D21 already
established: a shipped test going red is reported with its file, its line and what it asserts, and
is not edited to make this phase's own change pass.

T703/T704 put the upload form above the report's results (decisions.md D17) whenever the page's
`form` context variable is the one `ItemImportView` supplies — the preview state, and an ordinary
report reached by skipping the preview. Two tests written before D17 assert the opposite of exactly
that:

- `tests/test_ui/test_views.py:1699`
  (`TestItemImportPreview::test_a_preview_of_a_file_the_chosen_format_cannot_read_offers_no_confirmation`)
  asserts `"<form" not in content` for a preview whose file could not be read at all (AS-12: nothing
  would be created by confirming). That is precisely FR-023a's Retry scenario — the one D17 names as
  the item in this refinement with reasoning behind it — so the page now carries the upload form,
  its submit control reading *Retry*.
- `tests/test_ui/test_views.py:1791`
  (`TestItemImportSkipPreview::test_the_report_describes_what_was_imported_rather_than_what_would_be`)
  asserts `"<form" not in content` for the ordinary report a skip-preview submission produces. D17
  draws no exception for that path — "the form sits above the results on the report page" is the
  report page's own presentation now, not conditioned on how the report was reached — so this page
  carries the form too, reading *Import*.

**Chosen:** report both failures, their cause and their file and line, without editing either. The
same guardrail D20 and D21 record applies here: a failing pre-existing test is evidence about intent
the code may be contradicting, and the intent here changed at a decision recorded before this
phase's own code was written (D17, Sam's own reading of the shipped report). But the phase that
discovers a casualty of a sanctioned change is not the phase authorized to adjudicate it — its own
brief withheld that authorization, in the same words D21's brief did.

**Why defensible:** both tests are not wrong about what they once verified — a report page carrying
no control that re-runs the import. They are only wrong about the contract now. D20 already made the
matching edit once, for this same `TestImportReportPage` class, at a convergence step outside the
phase that motivated it; the correct move here is the same one, deferred the same way.

**A gap this same constraint leaves, named rather than silently accepted:** `ItemImportConfirmView`
never hands this template a `form` shaped like `ImportForm` — its own `form` is `ConfirmImportForm`,
which declares no fields, so `{% if form.fields.file %}` (the guard `import_report.html` uses to tell
the two apart without a new context flag) is false for every report that view produces, including the
`nothing_to_confirm` state, and including an ordinary report reached by confirming a preview — the
default path through this feature end to end. That report shows the back-to-catalogue and
empty-import-form buttons (FR-021), so a reader can always start a new import, but does not show the
upload form D17 describes sitting above the results. Closing this gap needs `ItemImportConfirmView`
to hand the template a real `ImportForm()`, which is `literature/ui/views.py`, out of this phase's
prohibited scope (prohibitions: "Do not change literature/ui/views.py... If a template genuinely
cannot reach something it needs, report that rather than changing the view").

**Revisit when:** whoever reviews this phase decides whether to bring the two tests onto the amended
contract (the move D20 made), and separately whether `ItemImportConfirmView` should hand the report
template an unbound `ImportForm()` alongside `ConfirmImportForm()` so the upload form's presence stops
depending on which of the two views rendered the page.
