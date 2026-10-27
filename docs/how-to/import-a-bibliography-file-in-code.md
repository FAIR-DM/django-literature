# Import a bibliography file in code

Import a BibTeX or RIS file from a script, a management command or a view of your own. A project
with the front end installed can also import from the catalogue, as in
[Import a bibliography file](import-a-bibliography-file.md).

## Steps

1. Optionally, rehearse the import first. Every stage runs and nothing is written:

   ```python
   from literature.importers import get_format

   with open("library.bib") as handle:
       preview = get_format("bibtex")().import_file(handle, dry_run=True)

   if not preview.ok:
       print(f"{len(preview.failed)} entries need attention first")
   ```

2. Import the file:

   ```python
   with open("library.bib") as handle:
       result = get_format("bibtex")().import_file(handle)
   ```

3. Report the entries that could not be stored:

   ```python
   print(f"{len(result.created)} stored, {len(result.failed)} could not be read")

   for entry in result.failed:
       label = entry.handle or f"entry {entry.index}"
       print(f"  {label}: {entry.reason}")
   ```

## The result

Every entry the file held is in `result`: under `created`, `skipped` or `failed`. One unreadable
entry does not stop the rest of the file. A name that is not configured raises `UnknownFormat`
from `get_format()`. The formats and exceptions are listed in
[`literature.importers`](../reference/api/importers.md).
