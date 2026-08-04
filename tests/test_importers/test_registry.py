"""Tests for the format registry (contracts/importers.md "The registry"), US3.

``import_file``'s string lookup (FR-018, T018) is exercised here too rather
than in a second set of fixtures, since it is the registry that makes a name
resolvable at all — tasks.md T016 groups both under one file.
"""

import io

import pytest

from literature.importers.base import BibFormat
from literature.importers.exceptions import FormatAlreadyRegistered, UnknownFormat
from literature.importers.registry import available_formats, get_format, register
from literature.importers.runner import import_file

from .conftest import make_echo_format


class TestRegister:
    def test_registered_format_is_enumerated(self):
        """FR-017."""
        fmt = make_echo_format([])
        register(fmt)

        assert available_formats()["echo"] is fmt

    def test_register_returns_its_argument_so_it_works_as_a_decorator(self):
        fmt = make_echo_format([])

        assert register(fmt) is fmt

    def test_registering_a_taken_name_raises_rather_than_replacing(self):
        """FR-020: the second registration fails, and the first still resolves."""
        first = make_echo_format([])
        second = make_echo_format([])
        register(first)

        with pytest.raises(FormatAlreadyRegistered):
            register(second)

        assert get_format("echo") is first

    def test_available_formats_cannot_be_mutated_by_the_caller(self):
        fmt = make_echo_format([])
        register(fmt)
        formats = available_formats()

        with pytest.raises(TypeError):
            formats["echo"] = None

        assert get_format("echo") is fmt


class TestGetFormat:
    def test_unregistered_name_raises_and_names_whats_registered(self):
        """FR-019."""
        register(make_echo_format([]))

        with pytest.raises(UnknownFormat) as excinfo:
            get_format("nonexistent")

        assert "echo" in str(excinfo.value)


@pytest.mark.django_db
class TestImportByName:
    def test_import_file_accepts_a_registered_name(self):
        """FR-018."""
        register(make_echo_format([{"kind": "good", "id": "a", "type": "book"}]))

        result = import_file(io.StringIO(), "echo")

        assert len(result.created) == 1

    def test_import_file_raises_for_an_unregistered_name_rather_than_failing_an_entry(self):
        """contracts/importers.md: UnknownFormat is programmer error and reaches
        the caller, rather than becoming a FAILED entry in the result."""
        with pytest.raises(UnknownFormat):
            import_file(io.StringIO(), "nonexistent")

    def test_result_records_the_name_used(self):
        """data-model.md: ``ImportResult.format_name`` is set when the import
        was run by name."""
        register(make_echo_format([{"kind": "good", "id": "a", "type": "book"}]))

        result = import_file(io.StringIO(), "echo")

        assert result.format_name == "echo"

    def test_result_format_name_is_none_when_a_class_was_passed_directly(self):
        result = import_file(io.StringIO(), make_echo_format([]))

        assert result.format_name is None


class TestRegisterRefusesWhatCannotBeAFormat:
    """contracts/importers.md: the contract raises for programmer error — "an
    unregistered format name, or something that is not a ``BibFormat``".

    Checked at registration rather than left to fail later. Without it, the
    first sign is an ``AttributeError`` from inside somebody's import run, a
    long way from the registration that caused it.
    """

    def test_something_that_is_not_a_format_is_refused(self):
        class NotAFormat:
            name = "impostor"

        with pytest.raises(TypeError):
            register(NotAFormat)

        assert "impostor" not in available_formats()

    def test_an_instance_rather_than_a_class_is_refused(self):
        with pytest.raises(TypeError):
            register(make_echo_format([])())

    def test_a_format_that_forgot_its_name_is_refused_by_name(self):
        """The message has to say which of the two things is missing, since
        ``AttributeError: type object 'X' has no attribute 'name'`` reads like
        a bug in the registry rather than an omission in the format.
        """
        nameless = make_echo_format([])
        del nameless.name

        with pytest.raises(TypeError, match="name"):
            register(nameless)

    def test_a_blank_name_is_refused(self):
        with pytest.raises(TypeError):
            register(make_echo_format([], format_name="   "))

    def test_a_format_missing_a_stage_is_refused_and_names_the_stage(self):
        """A subclass that leaves ``parse`` or ``to_csl_json`` unimplemented
        registers happily but cannot be instantiated, so the first sign is a
        raw ``TypeError`` from inside ``import_file`` — outside the exception
        vocabulary the contract documents, and a long way from the mistake.
        """

        class HalfFormat(BibFormat):
            name = "half"
            label = "Half a format"

            def parse(self, file):
                yield {}

        with pytest.raises(TypeError, match="to_csl_json"):
            register(HalfFormat)

        assert "half" not in available_formats()
