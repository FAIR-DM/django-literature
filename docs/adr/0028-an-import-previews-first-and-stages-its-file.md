# ADR-0028 — An import previews first, and stages its file against the session

- **Status:** Accepted
- **Context date:** spec 011 (FR-030 reversed, FR-031 amended, FR-038 through FR-044),
  `literature/ui/staging.py`, `literature/ui/views.py`, issue #108

## Context

The front end's import page was specified to import in one step: submit a file, and the references
exist by the time the report renders. Two rules followed from that. Nothing about a run was stored,
and the report page carried no control that could run anything again.

Using the shipped page showed why that ordering is the wrong way round. The report is the whole
point of the feature — it tells a reader what a file did to their catalogue — and a report that
arrives only after the fact cannot change the outcome it describes. Nothing here matches an entry
against what is already stored, deliberately (ADR-0009), so a reader who imports the wrong file
cannot fix it by importing the right one. They undo it by hand, and re-importing to check doubles
the damage.

The importer already had the capability the interface was declining to use: a dry run executes
every stage and reports identically, inside a transaction that is rolled back.

## Decision

Submitting the import form runs a dry run and renders its report labelled as a preview, with a
control that carries out the import it described. A checkbox on the form skips the preview and
imports in one step.

The uploaded file is staged on disk between the two requests. It has to be: a browser will not
re-populate a file input, and asking a reader to attach the file a second time to confirm it defeats
the point of previewing.

Three properties of that staging are the substance of this decision, because the obvious
implementation lacks all three. `django-import-export` solves the same problem the same way and is
what the design was read against.

- **The staged file's identity lives in the reader's session, never in the page.** Its confirm form
  posts the temporary filename back as a hidden field, and the permission check behind it returns
  true for any admin user unless a project configures otherwise, so anyone holding a name can confirm
  someone else's upload. Here the name is never rendered, so a request can confirm only what its own
  session staged.
- **The format is carried with the staged file, not re-read from the confirmation.** Theirs takes the
  format and the resource from the confirming request, so what commits is not guaranteed to be what
  was previewed. A confirmation also names which preview it is confirming, so a page still showing a
  preview that has since been replaced imports nothing rather than carrying out the later one. That
  identifier names nothing on disk and is checked against the confirming session's own value, so
  unlike a staged filename it reaches nothing on its own.
- **Abandoned stagings are swept.** Their removal is called in one place and not in a `finally`, so a
  preview that errors, or that the reader walks away from, leaves the file behind indefinitely. Every
  entry to the import page sweeps first.

Their exposure is bounded by the admin being staff-only. This front end has no permission model at
all (ADR-0022), so the same design without those three properties would be worse here than it is
there.

## Consequences

- Nothing is stored *about* a run: no import history, no record of who imported what. One file is
  held, it is removed when the import it was staged for is carried out, and abandoned ones are swept
  after a retention window. The rule that this package keeps no import history is untouched.
- The report page's promise that it runs nothing again is narrowed rather than kept: one submission
  imports exactly once, and no control on the page re-runs the import it is describing. The page now
  carries an upload form for a *new* import, which previewing is what makes safe.
- A confirmation whose staged file is gone — swept, already confirmed, staged by another session, or
  describing a preview this session has since replaced — says so and imports nothing, rather than
  failing.
- A session stages one file at a time. Previewing again discards what the previous preview staged, so
  an abandoned preview costs disk only until the next one, not for the whole retention window.
- The retention window is a judgement call rather than a derived figure. It is a module-level
  constant so a project can change it without touching the flow.
