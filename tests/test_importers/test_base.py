"""Tests for the ``Format`` contract itself (data-model.md, contracts/importers.md).

A format supplies exactly two stages and may override a third. FR-003 is the
point of this module: nothing here gives a format a route to the stage that
builds an ``Item``, so the test asserts the absence of extra surface, not
only the presence of the three sanctioned members.
"""

import abc

import pytest

from literature.importers.base import Format


class TestFormatIsAbstract:
    def test_cannot_instantiate_without_parse_and_to_csl_json(self):
        class Incomplete(Format):
            label = "Incomplete"

        Incomplete.name = "incomplete"

        with pytest.raises(TypeError):
            Incomplete()

    def test_cannot_instantiate_missing_only_parse(self):
        class NoParse(Format):
            label = "No parse"

            def to_csl_json(self, raw):
                return {}

        NoParse.name = "no-parse"

        with pytest.raises(TypeError):
            NoParse()

    def test_cannot_instantiate_missing_only_to_csl_json(self):
        class NoConvert(Format):
            label = "No convert"

            def parse(self, file):
                return iter([])

        NoConvert.name = "no-convert"

        with pytest.raises(TypeError):
            NoConvert()

    def test_is_an_abc(self):
        assert issubclass(Format, abc.ABC)


class TestHandleFor:
    def test_defaults_to_none(self):
        class Minimal(Format):
            label = "Minimal"

            def parse(self, file):
                return iter([])

            def to_csl_json(self, raw):
                return {}

        Minimal.name = "minimal"

        assert Minimal().handle_for(object()) is None

    def test_can_be_overridden(self):
        class WithHandles(Format):
            label = "With handles"

            def parse(self, file):
                return iter([])

            def to_csl_json(self, raw):
                return {}

            def handle_for(self, raw):
                return raw.upper()

        WithHandles.name = "with-handles"

        assert WithHandles().handle_for("smith2020") == "SMITH2020"


class TestFullSubclass:
    def test_a_subclass_supplying_all_three_works(self):
        class Full(Format):
            label = "Full"

            def parse(self, file):
                yield "raw-entry"

            def to_csl_json(self, raw):
                return {"type": "book", "id": raw}

            def handle_for(self, raw):
                return raw

        Full.name = "full"

        fmt = Full()
        assert list(fmt.parse(None)) == ["raw-entry"]
        assert fmt.to_csl_json("raw-entry") == {"type": "book", "id": "raw-entry"}
        assert fmt.handle_for("raw-entry") == "raw-entry"


class TestFormatHasNoRouteToBuildingAnItem:
    """FR-003: a format supplies parse, to_csl_json, and (optionally) handle_for.

    Nothing else — no hook, override point, or attribute reaches the stage
    that builds an ``Item``. Checked by enumerating the class's own public
    surface rather than only confirming the three sanctioned members exist,
    since the risk this test guards against is something *extra* being
    added, not something required being missing.
    """

    def test_public_surface_is_exactly_the_three_stages(self):
        public_attrs = {name for name in vars(Format) if not name.startswith("_")}
        assert public_attrs == {"parse", "to_csl_json", "handle_for"}
