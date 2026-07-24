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
    """ItemType completeness and schema agreement."""

    def test_has_45_values(self):
        """ItemType must have exactly 45 values per CSL JSON 1.0.2 schema."""
        assert len(ItemType.values) == 45

    def test_all_unique(self):
        """All 45 ItemType values must be unique (no accidental duplicates)."""
        assert len(ItemType.values) == len(set(ItemType.values))

    def test_values_match_schema(self):
        """ItemType values must match the authoritative csl-data.json schema exactly."""
        assert set(ItemType.values) == _SCHEMA_TYPES

    def test_underscore_types(self):
        """Exactly 4 ItemType values use underscores (CSL JSON 1.0.2 schema convention)."""
        underscored = [v for v in ItemType.values if "_" in v]
        assert sorted(underscored) == sorted(
            ["legal_case", "motion_picture", "musical_score", "personal_communication"]
        )

    def test_hyphenated_types(self):
        """Exactly 41 ItemType values use hyphens (or neither)."""
        non_underscored = [v for v in ItemType.values if "_" not in v]
        assert len(non_underscored) == 41


class TestNameRole:
    """NameRole completeness."""

    def test_has_26_values(self):
        """NameRole must have exactly 26 values per CSL JSON name-variable fields."""
        assert len(NameRole.values) == 26


class TestDateType:
    """DateType completeness."""

    def test_has_6_values(self):
        """DateType must have exactly 6 values per CSL JSON date-variable fields."""
        assert len(DateType.values) == 6


class TestIdentifierType:
    """IdentifierType completeness and known values."""

    def test_has_6_values(self):
        """IdentifierType must have exactly 6 values."""
        assert len(IdentifierType.values) == 6

    def test_known_values(self):
        """IdentifierType must contain the 6 known CSL identifier field names."""
        assert set(IdentifierType.values) == {"DOI", "ISBN", "ISSN", "PMID", "PMCID", "URL"}
