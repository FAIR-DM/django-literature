"""Tests for formats declared in the ``LITERATURE`` setting.

Tests set ``LITERATURE`` through the ``settings`` fixture so ``setting_changed`` fires both ways
and invalidates the module's cache. The fixture formats live at module level because a setting
can only name a real dotted path.
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


class BlankNameFormat(BibFormat):
    """A complete ``BibFormat`` subclass that forgot to set ``name``."""

    name = "   "
    label = "Blank name (test-only)"

    def parse(self, file):
        return iter([])

    def to_csl_json(self, raw):
        return {}


CONFIGURED_PATH = "tests.test_importers.test_config.ConfiguredFormat"
NOT_A_FORMAT_PATH = "tests.test_importers.test_config.NotABibFormat"
INCOMPLETE_PATH = "tests.test_importers.test_config.IncompleteFormat"
BLANK_NAME_PATH = "tests.test_importers.test_config.BlankNameFormat"
DOES_NOT_IMPORT_PATH = "tests.test_importers.test_config.DoesNotExist"


class TestAvailableFormats:
    def test_a_configured_format_is_enumerated(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}

        assert available_formats()["configured"] is ConfiguredFormat

    def test_an_unset_setting_yields_the_shipped_defaults(self):
        from literature.importers.bibtex import BibTeXFormat
        from literature.importers.ris import RISFormat

        assert dict(available_formats()) == {"bibtex": BibTeXFormat, "ris": RISFormat}

    def test_available_formats_cannot_be_mutated_by_the_caller(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}
        formats = available_formats()

        with pytest.raises(TypeError):
            formats["configured"] = None

        assert get_format("configured") is ConfiguredFormat

    def test_the_resolved_mapping_is_cached_across_calls(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}

        assert available_formats() is available_formats()

    def test_the_cache_is_invalidated_when_the_setting_changes(self, settings):
        # Without the setting_changed listener, every settings.LITERATURE override in this
        # file would leak into whichever test ran next.
        settings.LITERATURE = {"BIB_FORMATS": []}
        assert dict(available_formats()) == {}

        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}
        assert "configured" in available_formats()


@pytest.mark.django_db
class TestImportByName:
    def test_a_configured_name_can_be_named_in_an_import(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}

        result = get_format("configured")().import_file(io.StringIO("smith2020\n"))

        assert len(result.created) == 1
        assert result.format_name == "configured"

    def test_an_unconfigured_name_fails_naming_whats_configured(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": [CONFIGURED_PATH]}

        with pytest.raises(UnknownFormat) as excinfo:
            get_format("nonexistent")

        assert "configured" in str(excinfo.value)

    def test_an_unconfigured_name_says_so_when_nothing_is_configured(self):
        with pytest.raises(UnknownFormat) as excinfo:
            get_format("nonexistent")

        assert "nonexistent" in str(excinfo.value)


class TestAMisconfiguredEntryFailsAtFirstRead:
    def test_a_path_that_does_not_import_fails_naming_the_entry(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": [DOES_NOT_IMPORT_PATH]}

        with pytest.raises(ImproperlyConfigured, match="DoesNotExist"):
            available_formats()

    def test_a_path_that_is_not_a_bibformat_subclass_fails_naming_the_entry(
        self, settings
    ):
        settings.LITERATURE = {"BIB_FORMATS": [NOT_A_FORMAT_PATH]}

        with pytest.raises(ImproperlyConfigured, match="NotABibFormat"):
            available_formats()

    def test_a_format_missing_its_required_stages_fails_naming_the_entry(
        self, settings
    ):
        settings.LITERATURE = {"BIB_FORMATS": [INCOMPLETE_PATH]}

        with pytest.raises(ImproperlyConfigured, match="IncompleteFormat"):
            available_formats()

    def test_a_format_with_a_blank_name_fails_naming_the_entry(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": [BLANK_NAME_PATH]}

        with pytest.raises(ImproperlyConfigured, match="BlankNameFormat"):
            available_formats()


class TestAMisshapenSettingFailsAtFirstRead:
    def test_a_bare_list_says_the_setting_must_be_a_dict(self, settings):
        settings.LITERATURE = [CONFIGURED_PATH]

        with pytest.raises(ImproperlyConfigured, match="BIB_FORMATS"):
            available_formats()

    def test_a_single_path_written_without_a_list_names_the_value(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": CONFIGURED_PATH}

        with pytest.raises(ImproperlyConfigured, match=CONFIGURED_PATH):
            available_formats()

    def test_a_tuple_of_paths_is_accepted(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": (CONFIGURED_PATH,)}

        assert available_formats()["configured"] is ConfiguredFormat
