"""Pins that ``from_csl_json`` and ``from_csl_json_list`` are untouched.

FR-004: this feature reuses the existing CSL JSON conversion and must leave
its behaviour, for callers using it directly, exactly as it was.
``literature/converters.py`` is not modified by any task in this feature
(tasks.md notes) — the atomic savepoint lives in the runner instead
(research.md R4). The existing ``tests/test_converters.py`` already covers
``from_csl_json_list``'s skip-on-error behaviour; what it does not pin down
is that skipping still goes through ``logger.warning`` and not silently
(decision D5) — that is what this module adds.
"""

import logging

import pytest

from literature.converters import from_csl_json_list


@pytest.mark.django_db
class TestFromCslJsonListStillWarns:
    """decision D5: the contract's own reporting does not touch this function."""

    def test_skipping_an_invalid_item_logs_a_warning(self, caplog):
        data = [
            {"type": "article-journal", "citation-key": "Kept"},
            {"citation-key": "MissingType"},  # missing "type" -> ValidationError, skipped
        ]

        with caplog.at_level(logging.WARNING, logger="literature.converters"):
            items = from_csl_json_list(data)

        assert len(items) == 1
        assert items[0].citation_key == "Kept"
        assert any("Skipping invalid CSL JSON item" in record.message for record in caplog.records)
