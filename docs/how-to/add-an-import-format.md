# How to add an import format

Teach the importer a file format it does not read yet, so the format can be used from code and
from the front end's import form alongside BibTeX and RIS.

## Steps

1. Subclass `BibFormat`, and give it a `name` and a `label`:

   ```python
   from django.utils.translation import gettext_lazy as _

   from literature.importers import BibFormat, SkipEntry


   class BibTeXFormat(BibFormat):
       name = "bibtex"
       label = _("BibTeX")

       def parse(self, file):
           for block in iter_bibtex_blocks(file):   # yields, one at a time
               yield block

       def handle_for(self, raw):
           return raw.cite_key

       def to_csl_json(self, raw):
           if raw.entry_type in {"comment", "string", "preamble"}:
               raise SkipEntry(_("not a bibliographic entry"))
           return csl_json_from_bibtex(raw)
   ```

   `parse()` yields the file's entries one at a time, and `to_csl_json()` turns one entry into a
   CSL JSON record. `handle_for()` is optional: override it when the syntax gives entries names of
   their own, such as a cite key. Raise `SkipEntry` for something recognised that is not a
   reference, and `EntryError` for an entry that cannot be read.

2. Add its dotted path to the `BIB_FORMATS` key of the `LITERATURE` setting. The list replaces the
   default, so keep the formats you still want:

   ```python
   # settings.py
   LITERATURE = {
       "BIB_FORMATS": [
           "literature.importers.bibtex.BibTeXFormat",
           "literature.importers.ris.RISFormat",
           "myproject.formats.MyFormat",
       ],
   }
   ```

## The result

`get_format("bibtex")` returns the class, and the import form offers its `label`. The format gets
the whole workflow from `BibFormat`: the loop, the per-entry transaction, the dry run and the
report.

The other steps, `import_file`, `import_entries`, `import_entry`, `get_result` and the
`entry_created`, `entry_skipped` and `entry_failed` helpers, are ordinary methods that can be
overridden. What overriding them takes on is recorded in
[ADR 0006](../adr/0006-an-imported-entry-is-atomic.md) and
[ADR 0007](../adr/0007-the-import-runner-catches-everything.md). The setting is described in
[Settings](../reference/settings.md).
