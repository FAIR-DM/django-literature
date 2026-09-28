"""Tests for literature.choices enumerations.

Verifies completeness and correctness of all TextChoices enums
against the authoritative CSL JSON 1.0.2 schema in tests/data/csl-data.json.
"""

import json
import os

from literature.choices import DateType, IdentifierType, ItemType, NameRole

# Load the authoritative CSL schema once
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "data", "csl-data.json")
with open(_SCHEMA_PATH) as _f:
    _SCHEMA = json.load(_f)
_SCHEMA_TYPES = set(_SCHEMA["properties"]["type"]["enum"])


class TestItemType:
    def test_has_45_values(self):
        assert len(ItemType.values) == 45

    def test_all_unique(self):
        assert len(ItemType.values) == len(set(ItemType.values))

    def test_values_match_schema(self):
        assert set(ItemType.values) == _SCHEMA_TYPES

    def test_underscore_types(self):
        underscored = [v for v in ItemType.values if "_" in v]
        assert sorted(underscored) == sorted(
            ["legal_case", "motion_picture", "musical_score", "personal_communication"]
        )

    def test_hyphenated_types(self):
        non_underscored = [v for v in ItemType.values if "_" not in v]
        assert len(non_underscored) == 41


class TestNameRole:
    def test_has_26_values(self):
        assert len(NameRole.values) == 26


class TestDateType:
    def test_has_6_values(self):
        assert len(DateType.values) == 6


class TestIdentifierType:
    def test_has_6_values(self):
        assert len(IdentifierType.values) == 6

    def test_known_values(self):
        assert set(IdentifierType.values) == {
            "DOI",
            "ISBN",
            "ISSN",
            "PMID",
            "PMCID",
            "URL",
        }
