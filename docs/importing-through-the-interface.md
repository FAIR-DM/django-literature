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

## The preview

Submitting the form creates nothing. It puts the file aside and sends you to the preview, which
is a page at its own address, headed "Preview import" and saying beneath that heading that
nothing has been imported yet.

That page has no import form on it. The only file it can describe is the one you just submitted,
and it works that file out afresh each time you open it, so reloading the preview is safe: it
reads the same file again, reports the same outcomes, and writes nothing on either pass.

Where entries were skipped or could not be read, a warning above the table says so before you get
there. Where every entry would be created, there is no warning to read.

Below that is a line of counts — how many entries would be created, how many skipped, how many
failed — and then the table itself, one row per entry. At the foot of the page are three
controls.

### Narrowing the table

Between the counts and the table is a row of buttons: All, and one for each outcome. Each
outcome's button is the same colour as that outcome's badge in the table below it, so you can see
what a button will leave behind before you press it. Choosing Failed hides every row that is not a
failure, and All brings them back. Nothing is fetched and the page does not reload, because every
row of the report is already on it. However long the file, the whole report is on one page and
there is no second page to turn to.

The counts do not move when you narrow the table. They always describe the whole file. Narrow a
four-hundred-entry file down to its three failures and the counts still say how many of the four
hundred would be created, so three visible rows can never be misread as a file with only three
entries in it.

### What a row shows

Rows appear in the order the file held them, numbered from one. Each carries the entry's outcome
as a coloured badge — created, skipped and failed are each their own colour, so a failure or a
skip stands out without having to read every word — and, where the source format supplies one,
the entry's own citation key.

A row that would fail carries the reason. A skipped row carries a reason too, naming what was
recognised and set aside: a BibTeX comment or preamble block, RIS header material, or a record
carrying nothing but a reference type. A created entry needs no reason and carries none.

### The three controls

**Back to the catalogue** leaves without importing anything. Your file stays put, so you can
return to the preview afterwards and confirm it then.

**Restart import** throws the file away and opens an empty import form. Nothing is left behind to
confirm, and coming back to the preview address after restarting says as much.

**Confirm import** carries out exactly what the table described. You are not asked to attach the
file a second time.

## What confirming does

Confirming imports the file and returns you to the catalogue, with a message across the top
stating what was created: so many created, so many skipped, so many failed. There is no result
page. Every per-entry detail was on the preview you have just read, and what you want after an
import is your catalogue with the new references in it.

If you confirm a preview that has since been replaced by a newer one, or one whose file is no
longer there, you land back on the catalogue with a message saying there was nothing to confirm.
Nothing is imported in that case.

## When the format cannot read the file at all

Pick BibTeX for an RIS file and the preview still opens, but every entry on it is a failure and
nothing would be created. Confirming would import nothing, so the preview does not offer the
control. What is left at the foot of the page is Restart import and the way back to the
catalogue.

## Skipping the preview

Ticking "Skip the preview and import immediately" on the form bypasses all of the above. The
references are created in the same request that reads the file, and you land on a report that
describes what was imported rather than what would be. It carries the same counts and the same
one row per entry, and ends with a button back to the catalogue and a second that opens an empty
import form.

## How long a file waits

A file submitted for preview is held on disk only for as long as it takes you to confirm it. It
is tied to your own browser session, so nobody else can confirm what you put there, and it is
removed the moment you confirm. If you never confirm, it is cleared out automatically after 24
hours. Returning to a preview whose file has already gone, or reaching the preview address
without having submitted anything, says plainly that there is nothing to preview rather than
showing an empty page.

One file waits at a time. Previewing a second replaces the first, so a tab left open on the
earlier preview no longer has anything to confirm, and its Confirm import control says so rather
than importing the file you previewed afterwards.

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
