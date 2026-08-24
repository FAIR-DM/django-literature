# Importing a bibliography file

Alongside entering a reference by hand, the front end reads a bibliography file exported from
another tool and turns every entry it can into a reference.

## Reaching the page

The catalogue carries an Import action next to Add, on both presentations the front end can
serve — the table and the card list. Following it opens a page with a format choice and a file
control.

## Choosing a format and a file

The format list offers whatever formats the project has configured — BibTeX and RIS out of the
box, and anything else a project has added under the `LITERATURE` setting's `BIB_FORMATS` key.
Pick the one that matches the file, attach it, and submit.

The page does not look at the file to work this out for you. Choosing the wrong format is not
silently wrong: the format itself reports every entry it cannot make sense of, with a reason
such as "No BibTeX entries found. Is this a BibTeX file?" — the same message you would get
picking that format apart from the interface entirely.

The form also carries a checkbox, unticked by default, to skip the preview described below and
import in one step.

## Previewing before anything is imported

Submitting the form does not create anything by itself. It reads the file and shows you the same
report a real import would produce — every entry, its outcome, its reason where it has one —
under a heading stating plainly that nothing has been imported yet. Read it, and if it is what you
expect, a button on the page carries out the import it described. You are not asked to attach the
file a second time.

The uploaded file is held on disk only for as long as it takes you to confirm it. It is tied to
your own browser session, so nobody else can confirm what you staged, and it is removed the
moment you do confirm. If you never confirm, it is swept automatically after 24 hours — coming
back to a preview whose file has already been swept, or trying to confirm one from a different
session, tells you plainly that there is nothing to confirm and imports nothing.

Ticking "Skip the preview and import immediately" bypasses all of this: the references are
created in the same request that reads the file, and the report describes what was imported
rather than what would be.

## What the report shows

Every submission — a preview, a confirmation, or a one-step import — lands you on a report, never
back on the catalogue with a message. It states how many entries were created, skipped, and
failed, and lists one row per entry in the order the file held them, numbered from one.

Each row carries the entry's outcome as a coloured badge — created, skipped and failed are each
their own colour, so a failure or a skip stands out without having to read every word — and, where
the source format supplies one, its own citation key. A row for an entry that failed carries the
reason it failed, and a skipped row now carries a reason too, naming what was recognised and set
aside: a BibTeX comment or preamble block, RIS header material, or a record carrying nothing but a
reference type. A created row's position number links to the new reference. A skipped or failed
row's does not, because there is nothing to link to.

The upload form sits above the report, divided from it, so you can submit another file without
leaving the page. Where the attached file could not be read at all, that form's submit control
reads Retry and stays disabled until you attach a different file — resubmitting the same one would
only fail the same way. At the foot of the report, one button returns to the catalogue and a
second opens an empty import form.

The whole report is on one page, however many entries the file held — there is no further page to
turn to.

## Before you upload

A few things about how this works are worth knowing before you use it, particularly on a large or
a repeat upload:

- **Both the preview and the confirmed import run while you wait.** There is no background job —
  each request stays open for as long as reading the file, or creating the references, takes. How
  large a file the page will accept is bounded by your own project's upload size and request
  timeout, not by anything this page enforces itself.
- **Importing the same file twice creates the references twice.** Nothing checks whether an entry
  has already been imported before, so confirming the same file a second time adds a second copy
  of everything in it. The page states this before you submit.
- **A failure partway through does not undo what already succeeded.** Every entry is handled on
  its own, so the entries that were created before a failing one stay created — the report tells
  you what happened to each one individually rather than treating the file as all-or-nothing.
- **The page carries no permission check of its own.** It is reachable by anyone who can reach the
  catalogue, the same as every other page in the front end. A project that needs it restricted to
  particular users restricts it at its own routing, the same way it would guard any other view.
