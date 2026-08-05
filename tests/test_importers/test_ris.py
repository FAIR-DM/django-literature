"""Tests for the RIS format (spec 005).

One test module per source module, per the constitution's mirror rule. This is the foundational
phase only: the corpus, ``RISParser`` and the ``RISFormat`` skeleton. The RIS-to-CSL mapping is
US-1 (issue #36) and has no tests here yet — the checkpoint this module proves is "a ``.ris`` file
parses into entries and reports outcomes, with no mapping yet" (plan.md).

Corpus files live in ``tests/data/ris/``. See ``genuine/SOURCE.md`` for what each real export
carries and ``constructed/`` for the one file per malformation.
"""

import io
import itertools
import re
from pathlib import Path

import pytest

from literature.converters import _generate_dedup_suffix
from literature.importers import available_formats, get_format
from literature.importers.base import BibFormat
from literature.importers.exceptions import EntryError, ParseError
from literature.importers.results import Outcome
from literature.importers.ris import REFERENCE_TYPE_TABLE, RISEntry, RISFormat, RISParser
from literature.models import Item

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


def entry(ty="JOUR", index=0, **single_tags):
    """Build one :class:`RISEntry` directly, without going through the parser.

    ``single_tags`` names lowercase RIS tags (``ty``, ``au`` become ``TY``, ``AU``); a value that
    is a list becomes one ``(tag, value)`` pair per element, in order, which is how a repeatable
    tag (``AU``, ``A2``, ``SN``, ...) carries more than one value (``RISEntry.values``). This
    mirrors ``tests/test_importers/test_bibtex.py``'s own ``entry()`` builder for the sibling
    format, adapted for RIS's ordered-tuple entry shape rather than BibTeX's field dict.
    """
    tags = [("TY", ty)]
    for tag, value in single_tags.items():
        # A leading underscore lets a caller name a tag that collides with a Python keyword
        # (``_is`` for RIS's ``IS``), the same way ``is_`` would for a trailing collision.
        name = tag.lstrip("_").upper()
        values = value if isinstance(value, list) else [value]
        tags.extend((name, v) for v in values)
    return RISEntry(tags=tuple(tags), index=index, start_line=1)


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


class TestRISParserFraming:
    """Line grammar and entry framing: ``TY`` opens, ``ER`` or the next ``TY`` closes (T006)."""

    def test_yields_raw_tags_in_source_order(self):
        with fixture("constructed/missing_final_er.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert len(entries) == 1
        assert entries[0].tags == (
            ("TY", "JOUR"),
            ("AU", "Smith, J."),
            ("TI", "An entry whose closing ER tag was never written"),
            ("PY", "2020"),
        )

    def test_recovers_the_final_entry_when_er_is_missing(self):
        """FR-006: the last entry in a file whose closing ``ER`` is absent is still recovered."""
        with fixture("constructed/missing_final_er.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert len(entries) == 1
        assert entries[0].values("TY") == ["JOUR"]

    def test_closes_at_the_next_ty_when_er_is_missing_mid_file(self):
        with fixture("constructed/truncated_final_entry.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert len(entries) == 2
        assert entries[0].values("TI") == ["A complete entry recovered before the truncation"]
        assert entries[1].values("AU") == ["Jones,"]

    def test_entries_carry_their_index_in_source_order(self):
        with fixture("constructed/truncated_final_entry.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert [entry.index for entry in entries] == [0, 1]

    def test_the_first_entry_starts_at_line_one(self):
        with fixture("constructed/missing_final_er.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert entries[0].start_line == 1

    def test_a_later_entry_starts_at_its_own_ty_line(self):
        with fixture("constructed/truncated_final_entry.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert entries[1].start_line == 7

    def test_tolerates_the_single_space_separator_variant(self):
        with fixture("constructed/single_space_separator.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert entries[0].values("TY") == ["JOUR"]
        assert entries[0].values("AU") == ["Smith, J."]

    def test_tolerates_a_byte_order_mark(self):
        with fixture("constructed/byte_order_mark.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert len(entries) == 1
        assert entries[0].values("TY") == ["JOUR"]

    def test_tolerates_crlf_line_endings(self):
        with fixture("constructed/crlf_line_endings.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert len(entries) == 1
        assert entries[0].values("PY") == ["2020"]

    def test_an_empty_file_yields_no_entries(self):
        with fixture("constructed/empty.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert entries == []


class TestRISParserEncoding:
    """``utf-8-sig`` decoding, and a translatable ``ParseError`` naming the failure (FR-034, T006)."""

    def test_decodes_utf8_sig_and_strips_the_bom(self):
        with fixture("constructed/byte_order_mark.ris") as handle:
            entries = list(RISParser().parse(handle))
        # A leftover BOM character would corrupt TY's own value; it doesn't.
        assert entries[0].values("TY") == ["JOUR"]

    def test_raises_parse_error_naming_the_encoding_and_offset_on_undecodable_bytes(self):
        with fixture("constructed/cp1252_encoded.ris") as handle:
            with pytest.raises(ParseError) as excinfo:
                list(RISParser().parse(handle))
        message = str(excinfo.value)
        assert "utf-8" in message
        assert "18" in message


class TestRISParserStreaming:
    """Consuming one entry must not process the rest of a large file (FR-004, T006)."""

    def test_consuming_one_entry_leaves_the_remainder_unread(self, monkeypatch):
        real_pattern = RISParser._TAG_RE
        calls = []

        class _CountingPattern:
            def match(self, line):
                calls.append(line)
                return real_pattern.match(line)

        monkeypatch.setattr(RISParser, "_TAG_RE", _CountingPattern())

        with fixture("constructed/bulk_several_hundred_entries.ris") as handle:
            generator = RISParser().parse(handle)
            first = next(generator)

        assert first.index == 0
        # 500 entries at 5 lines each is 2500 lines; consuming only the first entry must not have
        # scanned anywhere close to that -- this is what fails if parse() is ever rewritten to
        # build a list before yielding.
        assert len(calls) < 20, f"scanned {len(calls)} lines to yield just the first entry"


class TestContinuationLines:
    """An untagged line resolves per tag: another value, or a joined continuation (FR-007, T007)."""

    def test_a_scalar_tag_continuation_is_joined_with_a_single_space(self):
        with fixture("constructed/wrapped_prose.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert entries[0].values("TI") == ["Tropical cyclones and the organization of mangrove forests: a review"]

    def test_a_prose_tag_continued_across_several_lines_joins_them_all(self):
        with fixture("constructed/wrapped_prose.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert entries[0].values("AB") == [
            "This abstract is written across several lines the way Web of Science wraps long "
            "prose, indented but not tagged, and must be read as one continuous value joined "
            "with spaces."
        ]

    def test_indentation_plays_no_part_in_the_scalar_join(self):
        """FR-007: indentation must not be used to decide -- only the tag is consulted."""
        with fixture("constructed/wrapped_prose.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert "   " not in entries[0].values("TI")[0]

    def test_a_repeatable_tags_continuation_lines_each_become_another_value(self):
        with fixture("constructed/endnote_multivalue_continuation.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert entries[0].values("KW") == ["article", "biostratigraphy", "Colorado", "dinosaur"]

    def test_a_second_repeatable_tag_in_the_same_entry_is_independent(self):
        with fixture("constructed/endnote_multivalue_continuation.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert entries[0].values("SN") == ["1932-8494", "1932-8486"]

    def test_repeatable_continuation_lines_are_not_joined_into_one_value(self):
        with fixture("constructed/endnote_multivalue_continuation.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert "biostratigraphy" not in entries[0].values("KW")[0]

    def test_a_tag_before_and_after_the_continued_one_is_unaffected(self):
        with fixture("constructed/endnote_multivalue_continuation.ris") as handle:
            entries = list(RISParser().parse(handle))
        assert entries[0].values("TI") == ["A new specimen described from several untagged continuation lines"]
        assert entries[0].values("PY") == ["2023"]


class TestWholeFileOutcomes:
    """The three whole-file outcomes and the header sentinel, through the full import workflow
    (``RISFormat.import_file``, not just ``RISParser`` directly) (T008).
    """

    def test_empty_file_succeeds_with_an_empty_result(self):
        with fixture("constructed/empty.ris") as handle:
            result = RISFormat().import_file(handle)
        assert result.ok
        assert list(result) == []

    def test_tag_lines_with_no_ty_anywhere_is_reported_as_a_failed_entry(self):
        with fixture("constructed/no_ty_anywhere.ris") as handle:
            result = RISFormat().import_file(handle)
        assert len(result) == 1
        assert result.entries[0].outcome == Outcome.FAILED
        assert "TY" in result.entries[0].reason

    def test_a_bibtex_file_under_a_ris_name_is_reported_as_a_failed_entry(self):
        with fixture("negative/bibtex_under_ris_name.ris") as handle:
            result = RISFormat().import_file(handle)
        assert len(result) == 1
        assert result.entries[0].outcome == Outcome.FAILED

    def test_a_wos_native_tagged_file_is_reported_as_a_failed_entry(self):
        with fixture("negative/wos_native_tagged.ris") as handle:
            result = RISFormat().import_file(handle)
        assert len(result) == 1
        assert result.entries[0].outcome == Outcome.FAILED

    def test_undecodable_bytes_are_reported_as_a_failed_entry_naming_the_encoding(self):
        with fixture("constructed/cp1252_encoded.ris") as handle:
            result = RISFormat().import_file(handle)
        assert len(result) == 1
        assert result.entries[0].outcome == Outcome.FAILED
        assert "utf-8" in result.entries[0].reason

    def test_header_material_is_reported_as_one_skipped_entry(self):
        with fixture("constructed/header_before_first_entry.ris") as handle:
            result = RISFormat().import_file(handle)
        assert result.entries[0].outcome == Outcome.SKIPPED

    def test_header_material_produces_no_item(self):
        with fixture("constructed/header_before_first_entry.ris") as handle:
            result = RISFormat().import_file(handle)
        assert result.entries[0].item is None

    def test_a_file_with_no_header_reports_no_skip_at_all(self):
        """A file that opens directly with ``TY`` owes no report for header material it never
        had (decisions.md D17)."""
        with fixture("constructed/missing_final_er.ris") as handle:
            result = RISFormat().import_file(handle)
        assert result.skipped == []

    def test_no_import_ever_raises_on_this_corpus(self):
        """SC-008: no content in a .ris file, however malformed, produces an unhandled error."""
        every_file = list((DATA / "constructed").glob("*.ris")) + list((DATA / "negative").glob("*.ris"))
        for path in every_file:
            with path.open("rb") as handle:
                RISFormat().import_file(handle)  # must not raise


class TestRegistration:
    """The format is reachable without configuration (FR-001, FR-003, FR-033, T009)."""

    def test_is_a_bibformat(self):
        assert issubclass(RISFormat, BibFormat)

    def test_names_itself(self):
        assert RISFormat.name == "ris"
        assert RISFormat.label

    def test_reachable_from_the_importers_namespace(self):
        """Not from ``literature`` itself, which stays empty on purpose (research 003 R3)."""
        import literature.importers as importers

        assert importers.RISFormat is RISFormat

    def test_shipped_by_default(self):
        """No configuration required (Article X, FR-003)."""
        assert "ris" in available_formats()

    def test_bibtex_is_still_shipped_alongside_it(self):
        """RIS is appended to DEFAULTS, not swapped in for BibTeX (FR-002)."""
        assert "bibtex" in available_formats()

    def test_resolvable_by_name(self):
        assert get_format("ris") is RISFormat

    def test_implements_the_stages_a_format_owns(self):
        assert not RISFormat.__abstractmethods__

    def test_imports_the_empty_file_fixture_when_resolved_by_name(self):
        with fixture("constructed/empty.ris") as handle:
            result = get_format("ris")().import_file(handle)
        assert result.ok
        assert list(result) == []


class TestGenerateDedupSuffix:
    """Regression for the citation-key de-duplication ceiling (issue #41, T041).

    ``_generate_dedup_suffix`` lives in ``literature/converters.py``, whose own mirror,
    ``tests/test_converters.py``, is this feature's evidence that T005 was a move and T041 an
    extension rather than a rewrite -- kept green and byte-for-byte unmodified (decisions.md D16).
    So this narrow regression lives here instead: RIS's minting is what makes suffix collision the
    normal case rather than the near-unreachable one BibTeX's own cite keys left it (plan.md "The
    de-duplication ceiling"), which is the same reasoning that put the fix itself in this feature's
    pull request. A dedicated ``tests/test_converters_dedup.py`` was tried first and rejected: the
    repo's own conformance check is file-path-based (forgekit/conformance.py), and a second test
    file for one source module fails it exactly as Article XIV's mirror rule says it should.

    Tests the generator directly, not by driving hundreds of entries through ``from_csl_json``:
    that route costs roughly one query per candidate suffix, and at the red step it hangs rather
    than failing.
    """

    def test_first_701_values_are_unchanged(self):
        """``tests/test_converters.py``'s own dedup tests pin the start of this sequence
        (``test_deduplication_appends_b``, ``test_deduplication_wrap_around``) -- extending it
        must not reorder what they already assert on.
        """
        singles = list("bcdefghijklmnopqrstuvwxyz")
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        pairs = ["".join(combo) for combo in itertools.product(alphabet, repeat=2)]
        expected = singles + pairs
        assert len(expected) == 701

        actual = list(itertools.islice(_generate_dedup_suffix("Smith2009"), 701))
        assert actual == expected

    def test_twenty_thousand_values_are_all_distinct(self):
        """Past the 701st value the sequence used to repeat forever (issue #41): once every
        two-letter suffix had been yielded, the outer ``while True`` started the two-letter
        product over from ``aa`` again, so ``_resolve_citation_key`` never terminated past 701
        collisions on the same base key.
        """
        values = list(itertools.islice(_generate_dedup_suffix("Smith2009"), 20_000))
        assert len(values) == len(set(values))


class TestReferenceTypeTable:
    """RIS reference type -> CSL item type, unknown to ``document`` (T010, FR-011)."""

    @pytest.mark.parametrize(("ris_type", "csl_type"), sorted(REFERENCE_TYPE_TABLE.items()))
    def test_every_listed_type_maps_to_its_csl_equivalent(self, ris_type, csl_type):
        assert RISFormat().to_csl_json(entry(ty=ris_type))["type"] == csl_type

    def test_an_unlisted_type_maps_to_the_generic_document(self):
        assert RISFormat().to_csl_json(entry(ty="ZZZZ"))["type"] == "document"

    def test_grnt_and_grant_reach_the_same_csl_type(self):
        assert RISFormat().to_csl_json(entry(ty="GRNT"))["type"] == RISFormat().to_csl_json(entry(ty="GRANT"))["type"]

    def test_unpd_and_unpb_reach_the_same_csl_type(self):
        assert RISFormat().to_csl_json(entry(ty="UNPD"))["type"] == RISFormat().to_csl_json(entry(ty="UNPB"))["type"]


class TestCoreFieldMapping:
    """Core RIS tag -> CSL variable, with the type-conditional cases (T011, FR-012)."""

    def test_title_lands_on_title(self):
        csl = RISFormat().to_csl_json(entry(ti="A new specimen of Haplocanthosaurus"))
        assert csl["title"] == "A new specimen of Haplocanthosaurus"

    def test_abstract_lands_on_abstract(self):
        csl = RISFormat().to_csl_json(entry(ab="A specimen is described."))
        assert csl["abstract"] == "A specimen is described."

    def test_short_title_lands_on_title_short(self):
        csl = RISFormat().to_csl_json(entry(st="A new specimen"))
        assert csl["title-short"] == "A new specimen"

    def test_volume_lands_on_volume(self):
        assert RISFormat().to_csl_json(entry(vl="24"))["volume"] == "24"

    def test_issue_lands_on_issue(self):
        assert RISFormat().to_csl_json(entry(_is="1"))["issue"] == "1"

    def test_language_lands_on_language(self):
        assert RISFormat().to_csl_json(entry(la="English"))["language"] == "English"

    def test_type_of_work_lands_on_genre(self):
        assert RISFormat().to_csl_json(entry(m3="Erratum"))["genre"] == "Erratum"

    def test_edition_lands_on_edition(self):
        assert RISFormat().to_csl_json(entry(et="3rd"))["edition"] == "3rd"

    def test_publisher_lands_on_publisher(self):
        assert RISFormat().to_csl_json(entry(pb="Elsevier"))["publisher"] == "Elsevier"

    def test_city_lands_on_publisher_place(self):
        assert RISFormat().to_csl_json(entry(cy="Amsterdam"))["publisher-place"] == "Amsterdam"

    def test_an_absent_core_tag_leaves_no_key(self):
        csl = RISFormat().to_csl_json(entry())
        assert not ({"title", "abstract", "volume", "issue"} & csl.keys())


class TestT2ContainerOrCollection:
    """``T2`` is a container title on article-like types and a collection title on book-like ones
    (T011, FR-012)."""

    def test_t2_is_container_title_on_jour(self):
        assert RISFormat().to_csl_json(entry(ty="JOUR", t2="Anatomical Record"))["container-title"] == (
            "Anatomical Record"
        )

    def test_t2_is_container_title_on_chap(self):
        """A chapter's ``T2`` genuinely names its containing book."""
        assert RISFormat().to_csl_json(entry(ty="CHAP", t2="Handbook of Paleontology"))["container-title"] == (
            "Handbook of Paleontology"
        )

    def test_t2_is_collection_title_on_book(self):
        """A whole book has no container of its own; a ``T2`` it carries names the series."""
        assert RISFormat().to_csl_json(entry(ty="BOOK", t2="Topics in Geology"))["collection-title"] == (
            "Topics in Geology"
        )

    def test_t2_is_collection_title_on_rprt(self):
        assert RISFormat().to_csl_json(entry(ty="RPRT", t2="Technical Report Series"))["collection-title"] == (
            "Technical Report Series"
        )


class TestSPLocatorOrPageCount:
    """``SP`` is a locator on types that have pages, a page count on types that do not (T011,
    FR-012, research.md R11)."""

    def test_sp_is_the_page_locator_on_jour(self):
        assert RISFormat().to_csl_json(entry(ty="JOUR", sp="20"))["page"] == "20"

    def test_sp_can_carry_a_whole_range_on_jour(self):
        assert RISFormat().to_csl_json(entry(ty="JOUR", sp="549-565"))["page"] == "549-565"

    def test_sp_is_the_page_count_on_book(self):
        assert RISFormat().to_csl_json(entry(ty="BOOK", sp="312"))["number-of-pages"] == "312"

    def test_sp_is_the_page_count_on_thes(self):
        assert RISFormat().to_csl_json(entry(ty="THES", sp="150"))["number-of-pages"] == "150"


class TestContributors:
    """Contributor tags become contributor records in source order, roles resolved on the
    reference type (T012, FR-013, FR-014)."""

    def test_authors_keep_source_order(self):
        csl = RISFormat().to_csl_json(entry(au=["Boisvert, C.", "Curtice, B.", "Wedel, M."]))
        assert csl["author"] == [
            {"family": "Boisvert", "given": "C."},
            {"family": "Curtice", "given": "B."},
            {"family": "Wedel", "given": "M."},
        ]

    def test_a2_is_editor_on_a_chapter_like_type(self):
        csl = RISFormat().to_csl_json(entry(ty="CHAP", a2="Editor, Enid"))
        assert csl["editor"] == [{"family": "Editor", "given": "Enid"}]
        assert "collection-editor" not in csl

    def test_a2_is_collection_editor_on_a_book_like_type(self):
        csl = RISFormat().to_csl_json(entry(ty="BOOK", a2="Editor, Enid"))
        assert csl["collection-editor"] == [{"family": "Editor", "given": "Enid"}]
        assert "editor" not in csl

    def test_a3_inverts_to_editor_on_book(self):
        csl = RISFormat().to_csl_json(entry(ty="BOOK", a3="Editor, Enid"))
        assert csl["editor"] == [{"family": "Editor", "given": "Enid"}]

    def test_a3_is_collection_editor_on_chap(self):
        csl = RISFormat().to_csl_json(entry(ty="CHAP", a3="Editor, Enid"))
        assert csl["collection-editor"] == [{"family": "Editor", "given": "Enid"}]

    def test_au_is_editor_on_edbook(self):
        csl = RISFormat().to_csl_json(entry(ty="EDBOOK", au="Editor, Enid"))
        assert csl["editor"] == [{"family": "Editor", "given": "Enid"}]
        assert "author" not in csl

    def test_au_is_author_on_jour(self):
        csl = RISFormat().to_csl_json(entry(ty="JOUR", au="Smith, J."))
        assert csl["author"] == [{"family": "Smith", "given": "J."}]

    def test_an_institutional_name_is_stored_as_a_literal(self):
        """No comma to split on: an unparsed or institutional name (FR-014)."""
        csl = RISFormat().to_csl_json(entry(au="World Wide Web Consortium"))
        assert csl["author"] == [{"literal": "World Wide Web Consortium"}]

    def test_no_contributor_tags_means_no_name_variable_keys(self):
        csl = RISFormat().to_csl_json(entry())
        assert not ({"author", "editor", "collection-editor"} & csl.keys())


class TestDates:
    """``PY`` anchors, ``DA`` refines precision, ``Y1`` falls back, ``Y2`` is the access date
    (T013, FR-015, FR-016)."""

    def test_py_alone_gives_year_precision(self):
        assert RISFormat().to_csl_json(entry(py="2024"))["issued"] == {"date-parts": [[2024]]}

    def test_da_refines_to_month_precision(self):
        csl = RISFormat().to_csl_json(entry(py="2024", da="2024/06"))
        assert csl["issued"] == {"date-parts": [[2024, 6]]}

    def test_da_refines_to_day_precision_with_no_padding(self):
        csl = RISFormat().to_csl_json(entry(py="2024", da="2024/06/24"))
        assert csl["issued"] == {"date-parts": [[2024, 6, 24]]}

    def test_da_with_a_disagreeing_year_is_not_used(self):
        """A ``DA`` that does not agree with ``PY``'s year is not a refinement of it; ``PY``'s own
        year precision is kept rather than trusting an inconsistent tag."""
        csl = RISFormat().to_csl_json(entry(py="2024", da="2023/06"))
        assert csl["issued"] == {"date-parts": [[2024]]}

    def test_y1_supplies_issued_when_py_is_absent(self):
        csl = RISFormat().to_csl_json(entry(y1="2020/03/15"))
        assert csl["issued"] == {"date-parts": [[2020, 3, 15]]}

    def test_py_takes_precedence_over_y1(self):
        csl = RISFormat().to_csl_json(entry(py="2024", y1="1999"))
        assert csl["issued"] == {"date-parts": [[2024]]}

    def test_y2_is_the_access_date(self):
        csl = RISFormat().to_csl_json(entry(y2="2023/01/10"))
        assert csl["accessed"] == {"date-parts": [[2023, 1, 10]]}
        assert "issued" not in csl

    def test_no_date_tags_means_no_issued_or_accessed(self):
        csl = RISFormat().to_csl_json(entry())
        assert not ({"issued", "accessed"} & csl.keys())


class TestIdentifiers:
    """``DO``/``UR`` become typed identifiers; ``SN`` resolves by shape then reference type
    (T014, FR-017)."""

    def test_do_becomes_doi(self):
        assert RISFormat().to_csl_json(entry(do="10.1002/ar.25520"))["DOI"] == "10.1002/ar.25520"

    def test_do_is_normalized_through_the_shared_doi_normalizer(self):
        """The resolver-URL form ``bibtex.py`` already handles (``IdentifierNormalizer``)."""
        csl = RISFormat().to_csl_json(entry(do="https://doi.org/10.1002/ar.25520"))
        assert csl["DOI"] == "10.1002/ar.25520"

    def test_ur_becomes_url(self):
        csl = RISFormat().to_csl_json(entry(ur="https://www.embase.com/search?id=1"))
        assert csl["URL"] == "https://www.embase.com/search?id=1"

    def test_sn_that_looks_like_an_issn_becomes_issn(self):
        assert RISFormat().to_csl_json(entry(ty="JOUR", sn="1932-8494"))["ISSN"] == "1932-8494"

    def test_sn_that_looks_like_an_isbn_becomes_isbn(self):
        assert RISFormat().to_csl_json(entry(ty="BOOK", sn="978-0-306-40615-7"))["ISBN"] == ("978-0-306-40615-7")

    def test_sn_on_rprt_is_a_report_number_not_an_identifier(self):
        csl = RISFormat().to_csl_json(entry(ty="RPRT", sn="NIST-8080"))
        assert csl["number"] == "NIST-8080"
        assert not ({"ISSN", "ISBN"} & csl.keys())

    def test_sn_on_pat_is_a_patent_number_not_an_identifier(self):
        csl = RISFormat().to_csl_json(entry(ty="PAT", sn="US1234567"))
        assert csl["number"] == "US1234567"
        assert not ({"ISSN", "ISBN"} & csl.keys())

    def test_no_identifier_tags_means_no_identifier_keys(self):
        csl = RISFormat().to_csl_json(entry())
        assert not ({"DOI", "URL", "ISSN", "ISBN", "number"} & csl.keys())


class TestCitationKeys:
    """``ID`` verbatim, otherwise minted deterministically; an entry too sparse to mint from falls
    back to its index; an overlong key fails the entry (T015, FR-019 through FR-023, FR-034)."""

    def test_id_tag_becomes_the_citation_key_verbatim(self):
        csl = RISFormat().to_csl_json(entry(id="889"))
        assert csl["citation-key"] == "889"

    def test_no_id_mints_from_family_year_and_title_word(self):
        csl = RISFormat().to_csl_json(entry(au="Boisvert, C.", py="2024", ti="Description of a new specimen"))
        assert csl["citation-key"] == "boisvert2024description"

    def test_a_leading_stopword_is_skipped_for_the_title_word(self):
        csl = RISFormat().to_csl_json(entry(au="Smith, J.", py="2020", ti="The organization of forests"))
        assert csl["citation-key"] == "smith2020organization"

    def test_minting_is_deterministic(self):
        raw = entry(au="Wedel, M.", py="2024", ti="A review of sauropods")
        assert RISFormat().to_csl_json(raw)["citation-key"] == RISFormat().to_csl_json(raw)["citation-key"]

    def test_an_entry_too_sparse_to_mint_from_falls_back_to_its_index(self):
        """No author, so family/year/title-word cannot all be built."""
        csl = RISFormat().to_csl_json(entry(py="2024", ti="A title with no author", index=7))
        assert csl["citation-key"] == "7"

    def test_handle_for_reports_the_same_key_as_to_csl_json(self):
        raw = entry(au="Boisvert, C.", py="2024", ti="Description of a new specimen")
        assert RISFormat().handle_for(raw) == RISFormat().to_csl_json(raw)["citation-key"]

    def test_an_overlong_verbatim_id_fails_the_entry_naming_the_limit(self):
        raw = entry(id="x" * 300)
        with pytest.raises(EntryError) as excinfo:
            RISFormat().to_csl_json(raw)
        assert "245" in str(excinfo.value)

    def test_an_overlong_minted_key_fails_the_entry_naming_the_limit(self):
        raw = entry(au=f"{'x' * 300},", py="2024", ti="Title")
        with pytest.raises(EntryError):
            RISFormat().to_csl_json(raw)


def _ris_bytes(*entries):
    """A minimal ``.ris`` file body, one entry per positional string, ready for
    ``RISFormat().import_file``."""
    return io.BytesIO("\n".join(entries).encode())


class TestReportedHandleIsTheStoredKey:
    """``entry_created`` reports the citation key as stored, suffix included, and a dry run still
    reports it while carrying no item (T016, FR-022, FR-002, SC-009)."""

    _ONE_ENTRY = "TY  - JOUR\nAU  - Smith, J.\nTI  - A title\nPY  - 2020\nID  - smith1\nER  -\n"

    @pytest.mark.django_db
    def test_a_created_entry_reports_its_stored_citation_key(self):
        result = RISFormat().import_file(_ris_bytes(self._ONE_ENTRY))
        assert result.created[0].handle == "smith1"
        assert result.created[0].item.citation_key == "smith1"

    @pytest.mark.django_db
    def test_a_colliding_key_is_reported_with_its_de_duplication_suffix(self):
        """Two entries in the same file minting the same key (T041's own de-duplication)."""
        result = RISFormat().import_file(_ris_bytes(self._ONE_ENTRY, self._ONE_ENTRY))
        assert [e.handle for e in result.created] == ["smith1", "smith1b"]
        assert {item.citation_key for item in Item.objects.all()} == {"smith1", "smith1b"}

    @pytest.mark.django_db
    def test_a_dry_run_still_reports_the_key_while_carrying_no_item(self):
        result = RISFormat().import_file(_ris_bytes(self._ONE_ENTRY), dry_run=True)
        assert result.created[0].handle == "smith1"
        assert result.created[0].item is None
        assert not Item.objects.exists()

    def test_delivered_by_overriding_entry_created(self):
        """SC-009: FR-022 is delivered by ``RISFormat`` overriding the documented
        ``entry_created`` override point, never by widening ``base.py``, ``results.py`` or
        ``converters.py`` (whose own suites, unmodified, are this feature's other evidence)."""
        assert "entry_created" in RISFormat.__dict__
        assert RISFormat.entry_created is not BibFormat.entry_created
