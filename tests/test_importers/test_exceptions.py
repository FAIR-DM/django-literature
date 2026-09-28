"""Tests for the importer exception vocabulary.

Three of these exceptions are how a format talks to the runner and never reach a
caller; two are the caller's problem and do. The distinction is the point of the
hierarchy, so it is asserted here rather than left to the runner's tests.
"""

from unittest import mock

import pytest
from django.utils.functional import Promise

from literature.importers import exceptions
from literature.importers.exceptions import (
    EntryError,
    ImporterError,
    ParseError,
    SkipEntry,
    UnknownFormat,
)


class TestHierarchy:
    @pytest.mark.parametrize(
        "exc_class",
        [SkipEntry, EntryError, ParseError, UnknownFormat],
    )
    def test_descends_from_importer_error(self, exc_class):
        assert issubclass(exc_class, ImporterError)

    def test_root_descends_from_exception(self):
        assert issubclass(ImporterError, Exception)

    @pytest.mark.parametrize("exc_class", [SkipEntry, EntryError, ParseError])
    def test_format_vocabulary_is_distinct_from_caller_facing(self, exc_class):
        assert not issubclass(exc_class, UnknownFormat)


# UnknownFormat is excluded from these: it builds its own message from a format
# name rather than taking one, and is covered by TestUnknownFormat below.
MESSAGE_CARRYING = [SkipEntry, EntryError, ParseError]


class TestMessages:
    @pytest.mark.parametrize("exc_class", MESSAGE_CARRYING)
    def test_carries_its_message(self, exc_class):
        assert "boom" in str(exc_class("boom"))

    @pytest.mark.parametrize("exc_class", MESSAGE_CARRYING)
    def test_accepts_a_lazy_message(self, exc_class):
        from django.utils.translation import gettext_lazy as _

        message = _("not a bibliographic entry")
        assert isinstance(message, Promise)
        assert str(exc_class(message)) == "not a bibliographic entry"

    def test_skip_entry_may_carry_no_message(self):
        assert str(SkipEntry()) == ""


class TestUnknownFormat:
    def test_lists_the_configured_names(self):
        exc = UnknownFormat("bibtex", available=["ris", "endnote"])
        text = str(exc)
        assert "bibtex" in text
        assert "ris" in text
        assert "endnote" in text

    def test_says_so_when_nothing_is_configured(self):
        text = str(UnknownFormat("bibtex", available=[]))
        assert "bibtex" in text
        assert text != ""

    def test_exposes_the_name_that_was_asked_for(self):
        assert UnknownFormat("bibtex", available=[]).name == "bibtex"

    def test_message_is_built_from_a_translatable_template(self):
        # Watches the gettext call: a bare f-string produces the same finished message, so
        # reading the text would stay green through the regression.
        seen = []

        def spy(message):
            seen.append(message)
            return message

        with mock.patch.object(exceptions, "_", spy):
            str(UnknownFormat("bibtex", available=["ris"]))

        assert seen, "the message was assembled without going through gettext"
        assert "{name}" in seen[0], (
            "the template must carry placeholders, not interpolated values"
        )

    def test_available_names_are_sorted(self):
        assert UnknownFormat("x", available=["ris", "bibtex"]).available == [
            "bibtex",
            "ris",
        ]
