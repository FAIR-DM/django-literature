"""Tests for the RIS format (spec 005).

One test module per source module, per the constitution's mirror rule. This is the foundational
phase only: the corpus, ``RISParser`` and the ``RISFormat`` skeleton. The RIS-to-CSL mapping is
US-1 (issue #36) and has no tests here yet — the checkpoint this module proves is "a ``.ris`` file
parses into entries and reports outcomes, with no mapping yet" (plan.md).

Corpus files live in ``tests/data/ris/``. See ``genuine/SOURCE.md`` for what each real export
carries and ``constructed/`` for the one file per malformation.
"""

import re
from pathlib import Path

import pytest

DATA = Path(__file__).parent.parent / "data" / "ris"


def fixture(relative_path):
    """Open a corpus file for reading, in binary mode.

    ``RISParser`` decodes the file itself (``utf-8-sig``, with a translatable
    ``ParseError`` on failure) rather than trusting the caller's mode, so
    every RIS fixture is opened in binary — the same way a caller handing
    over an uploaded file would (research.md R1: "the file is decoded
    utf-8-sig at the format's own read step").
    """
    return (DATA / relative_path).open("rb")


#: Fingerprints research.md R10 recorded for each genuine producer file,
#: checked byte-for-byte rather than assumed, so a corpus file silently
#: replaced by something else fails this test instead of every later one
#: that trusts it.
GENUINE_FINGERPRINTS = {
    "endnote.ris": (b"\nID  - ", b"\nKW  - article\nbiostratigraphy\n"),
    "scopus.ris": (b"DB  - Scopus", b"N1  - Export Date:", b"scopus.com/inward/record.uri"),
    "webofscience.ris": (b"AN  - WOS:", b"WE  - Science Citation Index Expanded"),
}


class TestGenuineCorpus:
    """The three producer exports research.md R10 vendors (FR-030, T001)."""

    def test_every_producer_file_is_present_and_non_empty(self):
        for name in GENUINE_FINGERPRINTS:
            content = (DATA / "genuine" / name).read_bytes()
            assert content, f"{name} is empty"

    def test_every_producer_file_carries_its_fingerprint(self):
        for name, fingerprints in GENUINE_FINGERPRINTS.items():
            content = (DATA / "genuine" / name).read_bytes()
            for needle in fingerprints:
                assert needle in content, f"{name} is missing its fingerprint {needle!r}"

    def test_scopus_and_webofscience_carry_a_byte_order_mark(self):
        for name in ("scopus.ris", "webofscience.ris"):
            content = (DATA / "genuine" / name).read_bytes()
            assert content.startswith(b"\xef\xbb\xbf"), f"{name} should carry a byte-order mark"

    def test_endnote_carries_no_byte_order_mark(self):
        content = (DATA / "genuine" / "endnote.ris").read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")

    def test_every_producer_file_holds_ten_entries(self):
        """The same ten references across all three (research.md R10)."""
        for name in GENUINE_FINGERPRINTS:
            content = (DATA / "genuine" / name).read_bytes()
            assert content.count(b"TY  - JOUR") == 10, name


#: The full constructed corpus, named rather than discovered, so a file added or removed without
#: updating this set fails here instead of quietly shrinking what T003 covers (see
#: test_bibtex.py's UNREADABLE_FIXTURES for the same convention).
CONSTRUCTED_FIXTURES = {
    "empty.ris",
    "missing_final_er.ris",
    "no_ty_anywhere.ris",
    "tag_block_no_ty_after_valid_entry.ris",
    "header_before_first_entry.ris",
    "byte_order_mark.ris",
    "crlf_line_endings.ris",
    "single_space_separator.ris",
    "wrapped_prose.ris",
    "endnote_multivalue_continuation.ris",
    "ty_only.ris",
    "truncated_final_entry.ris",
    "cp1252_encoded.ris",
    "long_unmapped_tag_value.ris",
    "bulk_several_hundred_entries.ris",
}


class TestConstructedCorpus:
    """One file per malformation the spec names, each isolating its own (T003).

    These assertions are structural — file presence and the byte-level shape
    each name promises — rather than behavioural, since ``RISParser`` does
    not exist yet at this point in the story. T006-T008 exercise several of
    these same files through the parser once it does.
    """

    def test_the_named_fixture_set_is_exactly_what_is_on_disk(self):
        on_disk = {p.name for p in (DATA / "constructed").glob("*.ris")}
        assert on_disk == CONSTRUCTED_FIXTURES

    def test_empty_file_is_truly_empty(self):
        assert (DATA / "constructed" / "empty.ris").read_bytes() == b""

    def test_missing_final_er_has_a_ty_and_no_er(self):
        content = (DATA / "constructed" / "missing_final_er.ris").read_text()
        assert content.count("TY  - ") == 1
        assert not any(line.startswith("ER") for line in content.splitlines())

    def test_no_ty_anywhere_has_tag_lines_but_no_ty(self):
        content = (DATA / "constructed" / "no_ty_anywhere.ris").read_text()
        assert "TY" not in content
        assert content.count(" - ") >= 2

    def test_tag_block_after_valid_entry_has_two_er_and_one_ty(self):
        content = (DATA / "constructed" / "tag_block_no_ty_after_valid_entry.ris").read_text()
        assert content.count("TY  - ") == 1
        assert content.count("ER  -") == 2

    def test_header_precedes_the_first_ty(self):
        content = (DATA / "constructed" / "header_before_first_entry.ris").read_text()
        assert content.index("Provider:") < content.index("TY  - ")

    def test_byte_order_mark_file_starts_with_a_bom(self):
        assert (DATA / "constructed" / "byte_order_mark.ris").read_bytes().startswith(b"\xef\xbb\xbf")

    def test_crlf_file_uses_crlf_throughout(self):
        content = (DATA / "constructed" / "crlf_line_endings.ris").read_bytes()
        assert b"\r\n" in content
        assert b"\n" not in content.replace(b"\r\n", b"")

    def test_single_space_separator_file_has_no_double_space_before_dash(self):
        content = (DATA / "constructed" / "single_space_separator.ris").read_text()
        assert "  - " not in content
        assert " - " in content

    def test_wrapped_prose_file_has_an_indented_continuation_line(self):
        content = (DATA / "constructed" / "wrapped_prose.ris").read_text()
        lines = content.splitlines()
        assert any(line.startswith("   ") for line in lines)

    def test_endnote_multivalue_file_has_unindented_continuation_lines(self):
        content = (DATA / "constructed" / "endnote_multivalue_continuation.ris").read_text()
        lines = content.splitlines()
        # "biostratigraphy" is a KW continuation line, unindented -- EndNote's own convention
        # (research.md R7), the opposite of the wrapped-prose fixture above.
        assert "biostratigraphy" in lines

    def test_ty_only_file_has_no_other_tag(self):
        content = (DATA / "constructed" / "ty_only.ris").read_text()
        tag_lines = [line for line in content.splitlines() if line.strip()]
        assert tag_lines == ["TY  - JOUR", "ER  -"]

    def test_truncated_file_has_a_complete_entry_and_an_incomplete_one(self):
        content = (DATA / "constructed" / "truncated_final_entry.ris").read_text()
        assert content.count("TY  - ") == 2
        assert content.count("ER  -") == 1

    def test_cp1252_file_is_not_valid_utf8(self):
        content = (DATA / "constructed" / "cp1252_encoded.ris").read_bytes()
        with pytest.raises(UnicodeDecodeError):
            content.decode("utf-8-sig")

    def test_long_unmapped_tag_value_exceeds_the_identifier_cap(self):
        content = (DATA / "constructed" / "long_unmapped_tag_value.ris").read_text()
        z9_line = next(line for line in content.splitlines() if line.startswith("Z9"))
        assert len(z9_line) > 500

    def test_bulk_file_holds_several_hundred_entries(self):
        content = (DATA / "constructed" / "bulk_several_hundred_entries.ris").read_text()
        assert content.count("TY  - ") == 500


#: The RIS tag-line grammar (plan.md "The parser" — R2 pins the exact separator, this is the
#: tolerant form the parser itself will use). Duplicated here rather than imported, since
#: ``RISParser`` does not exist yet at T004 — T006 is where the real one lands.
_TAG_LINE_RE = re.compile(r"^[A-Z][A-Z0-9]\s{0,2}-\s?.*$")

NEGATIVE_FIXTURES = {"wos_native_tagged.ris", "bibtex_under_ris_name.ris"}


class TestNegativeCorpus:
    """Files that are not RIS at all, under a ``.ris`` name (T004, research R10)."""

    def test_the_named_fixture_set_is_exactly_what_is_on_disk(self):
        on_disk = {p.name for p in (DATA / "negative").glob("*.ris")}
        assert on_disk == NEGATIVE_FIXTURES

    def test_neither_file_is_empty(self):
        for name in NEGATIVE_FIXTURES:
            assert (DATA / "negative" / name).read_bytes(), name

    def test_neither_file_contains_a_line_matching_the_ris_tag_grammar(self):
        """Isolates what makes each one "not RIS": no line the parser's own grammar would read
        as a tag, so a real ``RISParser`` finds nothing to frame an entry around (T006-T008).
        """
        for name in NEGATIVE_FIXTURES:
            content = (DATA / "negative" / name).read_text(encoding="utf-8", errors="replace")
            matching = [line for line in content.splitlines() if _TAG_LINE_RE.match(line)]
            assert matching == [], f"{name} has RIS-tag-shaped lines: {matching!r}"

    def test_wos_native_carries_its_own_two_letter_tags_with_no_dash(self):
        content = (DATA / "negative" / "wos_native_tagged.ris").read_text()
        assert "FN Clarivate Analytics Web of Science" in content

    def test_bibtex_file_carries_bibtex_syntax(self):
        content = (DATA / "negative" / "bibtex_under_ris_name.ris").read_text()
        assert content.startswith("@article{")
