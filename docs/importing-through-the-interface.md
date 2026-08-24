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

## What the report shows

Submitting lands you on a report, never back on the catalogue with a message. It states how many
entries were created, skipped, and failed, and lists one row per entry in the order the file held
them, numbered from one.

Each row carries the entry's outcome and, where the source format supplies one, its own citation
key. A row for an entry that failed also carries the reason. A created row's position number links
to the new reference. A skipped or failed row's does not, because there is nothing to link to.

The whole report is on one page, however many entries the file held — there is no further page to
turn to.

## Before you upload

A few things about how this works are worth knowing before you use it, particularly on a large or
a repeat upload:

- **The import runs while you wait.** There is no background job — the request stays open for as
  long as reading the file and creating the references takes. How large a file the page will
  accept is bounded by your own project's upload size and request timeout, not by anything this
  page enforces itself.
- **Importing the same file twice creates the references twice.** Nothing checks whether an entry
  has already been imported before, so running the same file through the page a second time adds
  a second copy of everything in it. The page states this before you submit.
- **A failure partway through does not undo what already succeeded.** Every entry is handled on
  its own, so the entries that were created before a failing one stay created — the report tells
  you what happened to each one individually rather than treating the file as all-or-nothing.
- **The page carries no permission check of its own.** It is reachable by anyone who can reach the
  catalogue, the same as every other page in the front end. A project that needs it restricted to
  particular users restricts it at its own routing, the same way it would guard any other view.
