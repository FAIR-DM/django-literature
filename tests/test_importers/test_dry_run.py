"""Tests for the dry-run rehearsal (contracts/importers.md), US2.

A dry run is the same code path as a real run, wrapped in one outer
``transaction.atomic()`` that is always rolled back (research.md R2, plan.md
"Design in brief" point 1). These tests assert the outward behaviour that
mechanism produces: every stage genuinely runs and every outcome is
reported, but nothing is stored.
"""

import io

import pytest

from literature.importers.results import Outcome
from literature.importers.runner import import_file
from literature.models import Item, ItemDate, ItemIdentifier, ItemName

from .conftest import DuplicateCustomIdentifier, make_echo_format


def _counts():
    return (
        Item.objects.count(),
        ItemName.objects.count(),
        ItemDate.objects.count(),
        ItemIdentifier.objects.count(),
    )


@pytest.mark.django_db
class TestDryRun:
    """FR-015, FR-016, SC-004."""

    def test_created_entries_are_reported_but_nothing_is_stored(self):
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "good", "id": "b", "type": "book"},
        ]
        before = _counts()

        result = import_file(io.StringIO(), make_echo_format(entries), dry_run=True)

        assert len(result.created) == 2
        assert _counts() == before

    def test_a_failing_entrys_reason_appears_identically(self):
        entries = [{"kind": "entry_error", "reason": "unrecognised item type", "id": "a"}]

        result = import_file(io.StringIO(), make_echo_format(entries), dry_run=True)

        assert len(result.failed) == 1
        assert result.failed[0].reason == "unrecognised item type"

    def test_result_states_whether_it_was_a_dry_run(self):
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        dry = import_file(io.StringIO(), make_echo_format(entries), dry_run=True)
        real = import_file(io.StringIO(), make_echo_format(entries))

        assert dry.dry_run is True
        assert real.dry_run is False

    def test_outcomes_match_the_equivalent_real_run(self):
        """US2 scenario 4: a dry run and a real run over the same file agree."""
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "entry_error", "reason": "bad", "id": "b"},
            {"kind": "skip", "reason": "a comment"},
            {"kind": "good", "id": "c", "type": "book"},
        ]
        fmt = make_echo_format(entries)

        dry = import_file(io.StringIO(), fmt, dry_run=True)
        real = import_file(io.StringIO(), fmt)

        assert [entry.outcome for entry in dry.entries] == [entry.outcome for entry in real.entries]
        assert [entry.reason for entry in dry.entries] == [entry.reason for entry in real.entries]
        assert [entry.handle for entry in dry.entries] == [entry.handle for entry in real.entries]

    def test_dry_run_entries_carry_no_item_even_when_created(self):
        """plan.md: exposing a rolled-back instance would hand back an object
        that looks saved and is not."""
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        result = import_file(io.StringIO(), make_echo_format(entries), dry_run=True)

        assert result.created[0].item is None

    def test_a_failing_entry_inside_a_dry_run_does_not_stop_the_rest(self):
        """The per-entry savepoint still protects the entries that follow,
        nested inside the outer rollback-only transaction."""
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "entry_error", "reason": "bad", "id": "b"},
            {"kind": "good", "id": "c", "type": "book"},
        ]
        before = _counts()

        result = import_file(io.StringIO(), make_echo_format(entries), dry_run=True)

        assert [entry.outcome for entry in result.entries] == [
            Outcome.CREATED,
            Outcome.FAILED,
            Outcome.CREATED,
        ]
        assert _counts() == before

    def test_a_database_level_failure_inside_a_dry_run_does_not_poison_the_rest(self, bypass_identifier_validation):
        """research.md R2's savepoint-per-entry mechanism, exercised with the
        outer dry-run transaction also open — a genuine IntegrityError nested
        inside the rollback-only outer block must not prevent the entry after
        it from being reported as created."""
        entries = [
            {"kind": "good", "id": "a", "type": "book", "custom": DuplicateCustomIdentifier()},
            {"kind": "good", "id": "b", "type": "book"},
        ]
        before = _counts()

        result = import_file(io.StringIO(), make_echo_format(entries), dry_run=True)

        assert len(result.failed) == 1
        assert len(result.created) == 1
        assert _counts() == before


@pytest.mark.django_db(transaction=True)
class TestDryRunOutsideATestTransaction:
    """The same guarantee at the transaction level a real caller runs at.

    Every test above runs under non-transactional ``django_db``, so the
    runner's outer ``transaction.atomic()`` is a savepoint nested in the test's
    own transaction and ``set_rollback(True)`` takes Django's
    ``savepoint_rollback`` path. A caller in autocommit hits the other branch:
    the block is outermost and the rollback is a real ``connection.rollback()``.
    Nothing else in the suite exercises it.
    """

    def test_a_dry_run_stores_nothing(self):
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "good", "id": "b", "type": "book"},
        ]
        before = _counts()

        result = import_file(io.StringIO(), make_echo_format(entries), dry_run=True)

        assert len(result.created) == 2
        assert _counts() == before

    def test_a_real_run_still_commits(self):
        """The counterpart: without the outer block, created entries persist."""
        entries = [{"kind": "good", "id": "a", "type": "book"}]
        items_before = Item.objects.count()

        result = import_file(io.StringIO(), make_echo_format(entries))

        assert len(result.created) == 1
        assert Item.objects.count() == items_before + 1


class SecondaryRouter:
    """Send every ``literature`` model to the ``secondary`` alias.

    What an installing project does when the catalogue lives somewhere other
    than its default database. This package is a reusable app, so that choice
    is never its own to make.
    """

    def db_for_read(self, model, **hints):
        return "secondary" if model._meta.app_label == "literature" else None

    db_for_write = db_for_read

    def allow_migrate(self, db, app_label, **hints):
        if app_label == "literature":
            return db == "secondary"
        return None


@pytest.mark.django_db(databases=["default", "secondary"], transaction=True)
class TestDryRunFollowsTheRouter:
    """FR-015 when the catalogue is not on the default connection.

    ``transaction.atomic()`` and ``set_rollback(True)`` both default to the
    ``default`` alias, while ``from_csl_json`` writes through whichever alias
    the router picks. When those differ, the outer transaction wrapped an idle
    connection and the rollback flag was set on it — so a dry run ran on the
    real connection with no transaction around it at all, committed every row,
    and reported ``dry_run=True`` with a list of created entries. The caller
    had no signal whatsoever.
    """

    @pytest.fixture(autouse=True)
    def _route_literature_elsewhere(self, settings):
        settings.DATABASE_ROUTERS = [SecondaryRouter()]

    def test_a_dry_run_stores_nothing_on_the_routed_database(self):
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "good", "id": "b", "type": "book"},
        ]

        result = import_file(io.StringIO(), make_echo_format(entries), dry_run=True)

        assert result.dry_run is True
        assert len(result.created) == 2
        assert Item.objects.count() == 0

    def test_a_real_run_still_commits_on_the_routed_database(self):
        result = import_file(io.StringIO(), make_echo_format([{"kind": "good", "id": "a", "type": "book"}]))

        assert len(result.created) == 1
        assert Item.objects.count() == 1
