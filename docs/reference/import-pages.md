# Import pages

The front end's pages for importing a bibliography file exported from another tool: the import
form, the preview, and the report of a one-step import. The steps are in
[Import a bibliography file](../how-to/import-a-bibliography-file.md).

## Reaching the import form

The table catalogue carries an Import action at the end of its toolbar, after the filters. The
card list carries no Import action, so a project serving the catalogue as cards links to the
`literature:item-import` route from its own navigation.

## The import form

- **Format.** The formats the project has configured: BibTeX and RIS out of the box, and any other
  a project has added under the `LITERATURE` setting's `BIB_FORMATS` key (see
  [Settings](settings.md)). The page does not look at the file to choose one. A format given a file
  it cannot read reports every entry it cannot make sense of, with a reason such as "No BibTeX
  entries found. Is this a BibTeX file?"
- **File.** The bibliography file.
- **Skip the preview and import immediately.** Unticked by default. Ticked, the file is imported in
  the same request and the one-step report is shown.

Submitting the form creates nothing. It stages the file and opens the preview.

## The preview

A page at its own address, headed "Preview import", saying beneath the heading that nothing has
been imported yet. It has no import form on it. It reads the staged file afresh each time it is
opened, so reloading it reports the same outcomes and writes nothing.

- **Warning.** Shown above the table when entries were skipped or could not be read. Absent when
  every entry would be created.
- **Counts.** How many entries would be created, skipped and failed. They describe the whole file,
  and do not change when the table is narrowed.
- **Outcome buttons.** All, and one for each outcome, each the colour of that outcome's badge.
  Choosing one hides every row with another outcome. Nothing is fetched and the page does not
  reload. The whole report is on one page, however long the file.
- **Table.** One row per entry, in the order the file held them, numbered from one. Each row shows
  the outcome as a coloured badge and, where the format supplies one, the entry's citation key. A
  failed row gives the reason. A skipped row gives what was recognised and set aside: a BibTeX
  comment or preamble block, RIS header material, or a record carrying nothing but a reference
  type. A created row gives no reason.
- **Back to the catalogue.** Leaves without importing. The staged file stays, so the preview can be
  confirmed later.
- **Restart import.** Discards the staged file and opens an empty import form. The preview address
  then says there is nothing to preview.
- **Confirm import.** Imports what the table described, without asking for the file again. Not
  shown when every entry failed, since nothing would be created.

## After confirming

The catalogue, with a message stating how many entries were created, skipped and failed. There is
no result page.

Confirming a preview that a newer one has replaced, or whose file is gone, returns to the catalogue
with a message saying there was nothing to confirm, and imports nothing.

## The one-step report

Shown when the preview is skipped. The references are already created. It has the same counts and
the same rows as the preview, and ends with a button back to the catalogue and a button that opens
an empty import form.

## Staged files

- A file staged for preview is tied to the browser session that staged it, so no other session can
  confirm it.
- It is removed when it is confirmed, and cleared automatically after 24 hours if it is not.
- A session stages one file at a time. Staging a second replaces the first, so a tab left open on
  the earlier preview has nothing to confirm, and its Confirm import says so.
- Opening the preview with nothing staged says there is nothing to preview.

## Limits

- **Both the preview and the confirmed import run during the request.** There is no background job.
  The largest file the page accepts is bounded by the project's upload size and request timeout.
- **Importing the same file twice creates its references twice.** Nothing checks whether an entry
  was imported before. The import form says so.
- **A failure partway through does not undo what succeeded.** Each entry is imported on its own.
- **Permission.** The form, the preview and Confirm import all require `literature.add_item`. A
  visitor who is not signed in is sent to sign in.
