"""Tests for the demo's seed catalogue — research.md R8, spec.md FR-010 through FR-015.

Reads ``demo/seed/catalogue.json`` as plain JSON: no Django app registry beyond what
pytest-django has already set up for the suite, no database, no subprocess (plan.md D-10).
The one exception is ``paginate_by``, which the list view inherits from django-mvp rather
than declaring itself, so it is read from the view's own attribute rather than hard-coded
here — an upstream default change would otherwise make this test assert the wrong number
silently (T011-paginate).

The role, date-slot and identifier-type vocabularies are imported from
``literature.choices`` rather than retyped by hand, for the same reason: retyping them is
a second copy that can drift from the source of truth without either copy failing.
"""

import json
from collections import defaultdict
from pathlib import Path

import pytest

from literature.choices import DateType, IdentifierType, NameRole
from literature.ui.views import ItemListView

_CATALOGUE_PATH = Path(__file__).resolve().parent.parent.parent / "demo" / "seed" / "catalogue.json"

_ROLE_KEYS = [role.value for role in NameRole]
_DATE_KEYS = [date_type.value for date_type in DateType]
_IDENTIFIER_KEYS = [identifier_type.value for identifier_type in IdentifierType]


def _contributors(entry):
    """All (role, name-dict) pairs an entry credits, across every CSL name-variable key."""
    pairs = []
    for role in _ROLE_KEYS:
        for name in entry.get(role, []):
            pairs.append((role, name))
    return pairs


def _name_key(name):
    """A hashable identity for a CSL name object, literal or family/given."""
    return (name.get("literal", ""), name.get("family", ""), name.get("given", ""))


def _entry_key(entry):
    """An entry's citation key, falling back to CSL JSON's bare ``id`` (converters.py:311-330)."""
    return entry.get("citation-key") or entry.get("id", "")


def _date_precision(date_variable):
    """'range', 'year', or the number of date-parts components, for a single date-variable."""
    date_parts = date_variable.get("date-parts", [])
    if len(date_parts) == 2:
        return "range"
    if len(date_parts) == 1:
        return "year" if len(date_parts[0]) == 1 else "other"
    return "other"


@pytest.fixture(scope="module")
def catalogue():
    return json.loads(_CATALOGUE_PATH.read_text())


@pytest.fixture(scope="module")
def paginate_by():
    return ItemListView.paginate_by


class TestSeedCatalogue:
    """The curated catalogue exercises every shape research.md R8 names."""

    def test_covers_at_least_ten_distinct_item_types(self, catalogue):
        types = {entry["type"] for entry in catalogue}
        assert len(types) >= 10

    def test_has_a_reference_with_eight_or_more_contributors(self, catalogue):
        counts = [len(_contributors(entry)) for entry in catalogue]
        assert max(counts) >= 8

    def test_has_a_reference_with_exactly_two_contributors(self, catalogue):
        counts = [len(_contributors(entry)) for entry in catalogue]
        assert 2 in counts

    def test_a_contributor_is_credited_on_two_references_under_two_different_roles(self, catalogue):
        roles_by_name = defaultdict(lambda: defaultdict(set))
        for entry in catalogue:
            for role, name in _contributors(entry):
                roles_by_name[_name_key(name)][role].add(_entry_key(entry))

        for roles in roles_by_name.values():
            if len(roles) < 2:
                continue
            references = set().union(*roles.values())
            if len(references) >= 2:
                return
        raise AssertionError("no contributor is credited under two different roles across two references")

    def test_has_a_year_only_date(self, catalogue):
        precisions = {
            _date_precision(entry[date_key]) for entry in catalogue for date_key in _DATE_KEYS if date_key in entry
        }
        assert "year" in precisions

    def test_has_a_full_date(self, catalogue):
        full_dates = [
            entry[date_key]
            for entry in catalogue
            for date_key in _DATE_KEYS
            if date_key in entry
            and len(entry[date_key].get("date-parts", [])) == 1
            and len(entry[date_key]["date-parts"][0]) == 3
        ]
        assert full_dates

    def test_has_a_date_range(self, catalogue):
        precisions = {
            _date_precision(entry[date_key]) for entry in catalogue for date_key in _DATE_KEYS if date_key in entry
        }
        assert "range" in precisions

    def test_has_identifiers_of_more_than_one_type_including_a_doi(self, catalogue):
        identifier_types_present = {key for entry in catalogue for key in _IDENTIFIER_KEYS if key in entry}
        assert len(identifier_types_present) >= 2
        assert "DOI" in identifier_types_present

    def test_has_exactly_one_reference_with_no_contributors_dates_or_identifiers(self, catalogue):
        def is_bare(entry):
            has_contributors = bool(_contributors(entry))
            has_dates = any(date_key in entry for date_key in _DATE_KEYS)
            has_identifiers = any(identifier_key in entry for identifier_key in _IDENTIFIER_KEYS)
            return not (has_contributors or has_dates or has_identifiers)

        bare_entries = [entry for entry in catalogue if is_bare(entry)]
        assert len(bare_entries) == 1

    def test_has_enough_references_to_paginate(self, catalogue, paginate_by):
        assert len(catalogue) > paginate_by
