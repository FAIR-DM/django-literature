"""The package as a whole: its public surface, and all three stories together.

Two things belong to ``literature.importers`` itself rather than to any one
submodule, so they live here: the surface the package publishes (FR-021,
Article X), and the end-to-end path (T022, SC-006).

Every other test in this package exercises one story against a format built by
a factory in ``conftest.py``. This one writes a format the way a real one will
be written — a class with two stages, an optional handle, and a settings
entry — and then uses the contract exactly as ``quickstart.md`` describes:
enumerate what is available, rehearse the file, import it, and check the
catalogue agrees with what the two results said.

The format below is the whole of what supporting a new syntax costs. Nothing in
``base.py``, ``results.py`` or ``converters.py`` knows it exists, which is the
claim SC-006 makes and this file is the standing demonstration of it.
"""

import importlib
import inspect
import io

import pytest
from django.utils.translation import gettext_lazy as _

import literature.importers as importers
from literature.importers import (
    BibFormat,
    EntryError,
    Outcome,
    SkipEntry,
    available_formats,
    get_format,
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


class LineFormat(BibFormat):
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
def smoke_format(settings):
    """Configure :class:`LineFormat`, as a package shipping a format would.

    Uses the ``settings`` fixture rather than mutating ``django.conf.settings``
    directly, so ``setting_changed`` fires and undoes it — and invalidates
    :mod:`literature.importers.config`'s cache — after the test.
    """
    settings.LITERATURE = {"BIB_FORMATS": ["tests.test_importers.test_smoke.LineFormat"]}
    return LineFormat


@pytest.mark.django_db
class TestTheWholeContract:
    def test_a_configured_format_is_enumerable_by_name_and_label(self, smoke_format):
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
        preview = get_format("smoke-lines")().import_file(io.StringIO(LIBRARY), dry_run=True)

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

        result = get_format("smoke-lines")().import_file(io.StringIO(LIBRARY))

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


#: Every name the contract publishes, and the submodule that defines it.
PUBLIC_SURFACE = {
    "BibFormat": "literature.importers.base",
    "ImporterError": "literature.importers.exceptions",
    "SkipEntry": "literature.importers.exceptions",
    "EntryError": "literature.importers.exceptions",
    "ParseError": "literature.importers.exceptions",
    "UnknownFormat": "literature.importers.exceptions",
    "get_format": "literature.importers.config",
    "available_formats": "literature.importers.config",
    "Outcome": "literature.importers.results",
    "EntryResult": "literature.importers.results",
    "ImportResult": "literature.importers.results",
    "BibTeXFormat": "literature.importers.bibtex",
}


class TestPublicSurface:
    def test_all_lists_exactly_the_documented_surface(self):
        """``__all__`` and the contract agree, in both directions.

        A name added to ``__all__`` but not to the contract fails here just as
        loudly as one added to the contract and never exported.
        """
        assert set(importers.__all__) == set(PUBLIC_SURFACE)

    @pytest.mark.parametrize("module", sorted(set(PUBLIC_SURFACE.values())))
    def test_every_public_name_a_submodule_defines_is_exported(self, module):
        """The half a hand-written list cannot catch.

        Both assertions above are derived from ``PUBLIC_SURFACE``, so a name
        added to a submodule and left out of *both* ``__all__`` and this file
        passes them without complaint — which is exactly the omission the
        guard is for. This one reads the submodules instead: anything they
        define without a leading underscore is public by Python's own
        convention, and must be reachable from the package (FR-021).
        """
        submodule = importlib.import_module(module)
        defined_here = {
            name
            for name, value in vars(submodule).items()
            if not name.startswith("_")
            and getattr(value, "__module__", None) == module
            and (inspect.isclass(value) or inspect.isfunction(value))
        }

        assert defined_here <= set(importers.__all__)

    @pytest.mark.parametrize("name", sorted(PUBLIC_SURFACE))
    def test_name_is_importable_from_the_package(self, name):
        """FR-021: reachable as ``literature.importers.<name>``."""
        assert hasattr(importers, name)

    @pytest.mark.parametrize(("name", "module"), sorted(PUBLIC_SURFACE.items()))
    def test_re_export_is_the_submodule_object_itself(self, name, module):
        """Not a copy, not a wrapper — the same object, so ``isinstance`` and
        ``except`` clauses behave identically whichever route a caller took.
        """
        assert getattr(importers, name) is getattr(importlib.import_module(module), name)
