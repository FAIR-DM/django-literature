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
    FormatAlreadyRegistered,
    ImporterError,
    ParseError,
    SkipEntry,
    UnknownFormat,
)


class TestHierarchy:
    """Every importer exception descends from one root."""

    @pytest.mark.parametrize(
        "exc_class",
        [SkipEntry, EntryError, ParseError, UnknownFormat, FormatAlreadyRegistered],
    )
    def test_descends_from_importer_error(self, exc_class):
        assert issubclass(exc_class, ImporterError)

    def test_root_descends_from_exception(self):
        assert issubclass(ImporterError, Exception)

    @pytest.mark.parametrize("exc_class", [SkipEntry, EntryError, ParseError])
    def test_format_vocabulary_is_distinct_from_caller_facing(self, exc_class):
        """A format's signals must not be catchable as caller-facing errors.

        The runner turns these into outcomes. If one were a subclass of
        UnknownFormat or FormatAlreadyRegistered, a caller's ``except`` around
        ``import_file`` would swallow an entry-level signal.
        """
        assert not issubclass(exc_class, (UnknownFormat, FormatAlreadyRegistered))


# UnknownFormat is excluded from these: it builds its own message from a format
# name rather than taking one, and is covered by TestUnknownFormat below.
MESSAGE_CARRYING = [SkipEntry, EntryError, ParseError, FormatAlreadyRegistered]


class TestMessages:
    """Each exception carries its message, and each message is translatable."""

    @pytest.mark.parametrize("exc_class", MESSAGE_CARRYING)
    def test_carries_its_message(self, exc_class):
        assert "boom" in str(exc_class("boom"))

    @pytest.mark.parametrize("exc_class", MESSAGE_CARRYING)
    def test_accepts_a_lazy_message(self, exc_class):
        """Reasons reach users, so a lazy translation must survive to str()."""
        from django.utils.translation import gettext_lazy as _

        message = _("not a bibliographic entry")
        assert isinstance(message, Promise)
        assert str(exc_class(message)) == "not a bibliographic entry"

    def test_skip_entry_may_carry_no_message(self):
        """Skipping is not an error, so a reason is optional."""
        assert str(SkipEntry()) == ""


class TestUnknownFormat:
    """The message must name what IS registered (FR-019)."""

    def test_lists_the_registered_names(self):
        exc = UnknownFormat("bibtex", available=["ris", "endnote"])
        text = str(exc)
        assert "bibtex" in text
        assert "ris" in text
        assert "endnote" in text

    def test_says_so_when_nothing_is_registered(self):
        """The empty case is the one a user hits first, before any format ships."""
        text = str(UnknownFormat("bibtex", available=[]))
        assert "bibtex" in text
        assert text != ""

    def test_exposes_the_name_that_was_asked_for(self):
        assert UnknownFormat("bibtex", available=[]).name == "bibtex"

    def test_message_is_built_from_a_translatable_template(self):
        """FR-022: the message goes through gettext rather than an f-string.

        Asserted by watching the translation call, not by reading the finished
        message. The previous version wrapped ``translation.override("en")``
        around the message and checked that the format name and the registered
        names appeared in it — which a bare f-string satisfies exactly as well,
        so it would have stayed green through the very change it exists to
        catch.
        """
        seen = []

        def spy(message):
            seen.append(message)
            return message

        with mock.patch.object(exceptions, "_", spy):
            str(UnknownFormat("bibtex", available=["ris"]))

        assert seen, "the message was assembled without going through gettext"
        assert "{name}" in seen[0], "the template must carry placeholders, not interpolated values"

    def test_available_names_are_sorted(self):
        """Order should not depend on registration order, or the message churns."""
        assert UnknownFormat("x", available=["ris", "bibtex"]).available == ["bibtex", "ris"]
