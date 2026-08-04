"""One file, all three stories together (T022, SC-006).

Every other test in this package exercises one story against a format built by
a factory in ``conftest.py``. This one writes a format the way a real one will
be written — a class with two stages, an optional handle, and a registration —
and then uses the contract exactly as ``quickstart.md`` describes: enumerate
what is available, rehearse the file, import it, and check the catalogue agrees
with what the two results said.

The format below is the whole of what supporting a new syntax costs. Nothing in
``runner.py``, ``results.py`` or ``converters.py`` knows it exists, which is the
claim SC-006 makes and this file is the standing demonstration of it.
"""

import io

import pytest
from django.utils.translation import gettext_lazy as _

from literature.importers import (
    EntryError,
    Format,
    Outcome,
    SkipEntry,
    available_formats,
    import_file,
    register,
)
from literature.models import Item

#: A toy syntax: one record per line, ``key | type | title``, ``#`` for a note.
LIBRARY = """\
kuhn1962 | book | The Structure of Scientific Revolutions
# exported by hand, 2011 — the two lines below have never worked
notype | | Something without a type
halfaline | book
popper1959 | book | The Logic of Scientific Discovery
"""


class LineFormat(Format):
    """A bibliographic syntax in the smallest form the contract allows."""

    name = "smoke-lines"
    label = _("Pipe-separated lines (test-only)")

    def parse(self, file):
        for line in file:
            line = line.strip()
            if line:
                yield line

    def handle_for(self, raw):
        if raw.startswith("#"):
            return None
        return raw.split("|")[0].strip() or None

    def to_csl_json(self, raw):
        if raw.startswith("#"):
            raise SkipEntry(_("a note, not a bibliographic entry"))
        parts = [part.strip() for part in raw.split("|")]
        if len(parts) != 3:
            # A format reports what it cannot read rather than letting the
            # error escape, so the rest of the file still imports.
            raise EntryError(_("expected 'key | type | title', got {count} fields").format(count=len(parts)))
        key, item_type, title = parts
        return {"citation-key": key, "type": item_type, "title": title}


@pytest.fixture
def smoke_format():
    """Register :class:`LineFormat`, as a package shipping a format would.

    Undone after the test by the autouse ``isolated_registry`` fixture.
    """
    return register(LineFormat)


@pytest.mark.django_db
class TestTheWholeContract:
    def test_a_registered_format_is_enumerable_by_name_and_label(self, smoke_format):
        """US3: a caller that knows nothing about formats can list them."""
        formats = available_formats()

        assert formats["smoke-lines"] is LineFormat
        assert str(formats["smoke-lines"].label) == "Pipe-separated lines (test-only)"

    def test_rehearse_then_import_agrees_with_the_catalogue(self, smoke_format):
        """US1, US2 and US3 in one run, by name, over a mixed file.

        The rehearsal and the real run see the same entries with the same
        outcomes in the same order, the rehearsal stores nothing, and what the
        real run reported as created is exactly what ends up in the catalogue.
        """
        preview = import_file(io.StringIO(LIBRARY), "smoke-lines", dry_run=True)

        assert preview.dry_run is True
        assert [entry.outcome for entry in preview] == [
            Outcome.CREATED,
            Outcome.SKIPPED,
            Outcome.FAILED,
            Outcome.FAILED,
            Outcome.CREATED,
        ]
        assert preview.ok is False
        assert [entry.handle for entry in preview.failed] == ["notype", "halfaline"]
        assert all(entry.reason for entry in preview.failed)
        assert all(entry.item is None for entry in preview)
        assert Item.objects.count() == 0, "a rehearsal must leave the catalogue untouched"

        result = import_file(io.StringIO(LIBRARY), "smoke-lines")

        assert result.dry_run is False
        assert result.format_name == "smoke-lines"
        assert [entry.outcome for entry in result] == [entry.outcome for entry in preview]
        assert [entry.handle for entry in result] == [entry.handle for entry in preview]

        assert Item.objects.count() == len(result.created) == 2
        assert {item.pk for item in Item.objects.all()} == {entry.item.pk for entry in result.created}
        assert set(Item.objects.values_list("title", flat=True)) == {
            "The Structure of Scientific Revolutions",
            "The Logic of Scientific Discovery",
        }
