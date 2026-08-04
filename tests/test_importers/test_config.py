"""Tests for settings-declared formats (contracts/importers.md "The registry"), US3.

Replaces ``test_registry.py`` (T028 deletes it): a format is no longer
registered by decorating it and holding it in module-level state, it is
declared by dotted path in the ``LITERATURE`` setting and resolved on read.
``import_file``'s name-based lookup (FR-018, T018) is exercised here too,
same as it was in the file this replaces, since it is ``get_format`` that
makes a name resolvable at all.

Every test that sets ``LITERATURE`` uses the ``settings`` fixture rather
than mutating ``django.conf.settings`` directly, so ``django.test.signals``'
``setting_changed`` fires on the way in *and* on the way out — the signal
``literature.importers.config`` listens for to invalidate its cache. Two
formats used only as fixtures (:class:`ConfiguredFormat`, :class:`NotABibFormat`,
:class:`IncompleteFormat`) are defined at module level, because settings
resolution needs a real dotted import path — a class built by a factory
closure, the way ``conftest.py``'s other formats are, has no path a setting
could name.
"""

import io

import pytest
from django.core.exceptions import ImproperlyConfigured

from literature.importers.base import BibFormat
from literature.importers.config import available_formats, get_format
from literature.importers.exceptions import UnknownFormat


class ConfiguredFormat(BibFormat):
    """A minimal format, reachable by dotted path for settings resolution."""

    name = "configured"
    label = "Configured (test-only)"

    def parse(self, file):
        for line in file:
            line = line.strip()
            if line:
                yield line

    def to_csl_json(self, raw):
        return {"id": raw, "type": "book", "title": raw}


class NotABibFormat:
    """Importable, but not a ``BibFormat`` subclass — a misconfigured entry."""


class IncompleteFormat(BibFormat):
    """A ``BibFormat`` subclass that never implements its two required stages."""

    name = "incomplete"
    label = "Incomplete (test-only)"


CONFIGURED_PATH = "tests.test_importers.test_config.ConfiguredFormat"
NOT_A_FORMAT_PATH = "tests.test_importers.test_config.NotABibFormat"
INCOMPLETE_PATH = "tests.test_importers.test_config.IncompleteFormat"
DOES_NOT_IMPORT_PATH = "tests.test_importers.test_config.DoesNotExist"


class TestAvailableFormats:
    def test_a_configured_format_is_enumerated(self, settings):
        """FR-017."""
        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}

        assert available_formats()["configured"] is ConfiguredFormat

    def test_an_unset_setting_yields_the_shipped_defaults(self):
        """FR-020: the built-in behaviour works with no configuration
        (Article X) — this package ships no format of its own yet, so the
        default is an empty mapping, not an error."""
        assert dict(available_formats()) == {}

    def test_available_formats_cannot_be_mutated_by_the_caller(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}
        formats = available_formats()

        with pytest.raises(TypeError):
            formats["configured"] = None

        assert get_format("configured") is ConfiguredFormat

    def test_the_resolved_mapping_is_cached_across_calls(self, settings):
        """The setting is read once per process, not once per call — proven
        by asking twice without changing anything in between and getting the
        identical object back, not merely an equal one."""
        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}

        assert available_formats() is available_formats()

    def test_the_cache_is_invalidated_when_the_setting_changes(self, settings):
        """``override_settings``/the ``settings`` fixture fires
        ``setting_changed``, which this module listens for — without that,
        this test (and every use of ``settings.LITERATURE`` in this file)
        would leak into whichever test ran next."""
        settings.LITERATURE = {"BIB_FORMATS": []}
        assert dict(available_formats()) == {}

        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}
        assert "configured" in available_formats()


@pytest.mark.django_db
class TestImportByName:
    def test_a_configured_name_can_be_named_in_an_import(self, settings):
        """FR-018."""
        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}

        result = get_format("configured")().import_file(io.StringIO("smith2020\n"))

        assert len(result.created) == 1
        assert result.format_name == "configured"

    def test_an_unconfigured_name_fails_naming_whats_configured(self, settings):
        """FR-019."""
        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}

        with pytest.raises(UnknownFormat) as excinfo:
            get_format("nonexistent")

        assert "configured" in str(excinfo.value)

    def test_an_unconfigured_name_says_so_when_nothing_is_configured(self):
        with pytest.raises(UnknownFormat) as excinfo:
            get_format("nonexistent")

        assert "nonexistent" in str(excinfo.value)


class TestAMisconfiguredEntryFailsAtFirstRead:
    """FR-017 scenario 5: an entry that does not resolve, or resolves to
    something unusable, fails naming the offending entry rather than
    surfacing later as a format silently missing from the enumerated set.
    """

    def test_a_path_that_does_not_import_fails_naming_the_entry(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": [DOES_NOT_IMPORT_PATH]}

        with pytest.raises(ImproperlyConfigured, match="DoesNotExist"):
            available_formats()

    def test_a_path_that_is_not_a_bibformat_subclass_fails_naming_the_entry(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": [NOT_A_FORMAT_PATH]}

        with pytest.raises(ImproperlyConfigured, match="NotABibFormat"):
            available_formats()

    def test_a_format_missing_its_required_stages_fails_naming_the_entry(self, settings):
        """A subclass that never implements ``parse``/``to_csl_json`` would
        otherwise resolve cleanly and fail later with a raw ``TypeError``
        from inside ``import_file`` — outside the exception vocabulary the
        contract documents, and a long way from the misconfiguration."""
        settings.LITERATURE = {"BIB_FORMATS": [INCOMPLETE_PATH]}

        with pytest.raises(ImproperlyConfigured, match="IncompleteFormat"):
            available_formats()
