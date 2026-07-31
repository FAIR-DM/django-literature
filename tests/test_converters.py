"""Tests for literature.converters module (US2 — Convert Between Model and CSL JSON).

Tests cover contract from contracts/csl-json.md:
- to_csl_json(): serialization guarantees, blank field omission, name ordering,
  identifier placement, fixture round-trip, parametrized type round-trips
- from_csl_json(): validation errors, citation-key resolution, deduplication,
  date round-trips, literal names, unknown identifiers
- from_csl_json_list(): batch import with skip-on-error semantics
- round trip: a fully populated item survives model -> CSL JSON -> model unchanged
"""

import json
import os

import pytest
from django.core.exceptions import ValidationError
from partial_date import PartialDate

from literature.choices import DateType, IdentifierType, ItemType, NameRole
from literature.converters import from_csl_json, from_csl_json_list, to_csl_json
from literature.models import Item, ItemDate, ItemIdentifier, ItemName, Name
from tests.factories import ItemDateFactory, ItemFactory, ItemIdentifierFactory, ItemNameFactory, NameFactory

# Load the real-world fixture
_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "data", "publication-csl.json")
with open(_FIXTURE_PATH) as _f:
    _FIXTURE_CSL = json.load(_f)


def _item_scalar_field_names() -> list[str]:
    """Every Item field that to_csl_json() treats as a plain scalar column.

    Mirrors the skip set in ``to_csl_json()`` so this list tracks the model
    automatically as fields are added, instead of a hand-maintained duplicate.
    """
    skip = {"id", "pk", "citation_key", "type", "categories", "custom", "created", "modified"}
    return [f.name for f in Item._meta.get_fields() if hasattr(f, "attname") and f.name not in skip]


@pytest.mark.django_db
class TestToCslJson:
    """Serialization from Item to CSL JSON."""

    def test_always_has_id_and_type(self):
        """to_csl_json() output always has 'id' and 'type' keys."""
        item = ItemFactory(citation_key="Test2024", type=ItemType.BOOK)
        result = to_csl_json(item)
        assert "id" in result
        assert result["id"] == "Test2024"
        assert "type" in result
        assert result["type"] == ItemType.BOOK

    def test_omits_blank_fields(self):
        """to_csl_json() omits blank/null optional fields."""
        item = ItemFactory(citation_key="Minimal2024", type=ItemType.ARTICLE)
        result = to_csl_json(item)
        assert "abstract" not in result
        assert "title" not in result
        assert "publisher" not in result

    def test_includes_non_blank_fields(self):
        """to_csl_json() includes non-blank fields with correct CSL JSON keys."""
        item = ItemFactory(
            citation_key="Full2024",
            type=ItemType.ARTICLE_JOURNAL,
            title="My Title",
            volume="3",
            issue="1",
            page="10-20",
            language="en",
            container_title="Some Journal",
        )
        result = to_csl_json(item)
        assert result["title"] == "My Title"
        assert result["volume"] == "3"
        assert result["issue"] == "1"
        assert result["page"] == "10-20"
        assert result["language"] == "en"
        assert result["container-title"] == "Some Journal"

    def test_name_arrays_ordered(self, item):
        """to_csl_json() exports name arrays in order."""
        n1 = NameFactory(family="Alpha", given="A")
        n2 = NameFactory(family="Beta", given="B")
        n3 = NameFactory(family="Gamma", given="G")
        ItemNameFactory(item=item, name=n1, role=NameRole.AUTHOR, order=0)
        ItemNameFactory(item=item, name=n2, role=NameRole.AUTHOR, order=1)
        ItemNameFactory(item=item, name=n3, role=NameRole.AUTHOR, order=2)
        result = to_csl_json(item)
        assert "author" in result
        assert [a["family"] for a in result["author"]] == ["Alpha", "Beta", "Gamma"]

    def test_known_identifier_as_top_level_key(self, item):
        """to_csl_json() places known identifiers as top-level CSL JSON keys."""
        ItemIdentifierFactory(item=item, type=IdentifierType.DOI, value="10.1234/test")
        ItemIdentifierFactory(item=item, type=IdentifierType.ISSN, value="0956-540X")
        result = to_csl_json(item)
        assert result["DOI"] == "10.1234/test"
        assert result["ISSN"] == "0956-540X"

    def test_unknown_identifier_in_custom(self, item):
        """to_csl_json() places unknown identifier types in the custom object."""
        ItemIdentifierFactory(item=item, type="arXiv", value="2103.12345")
        result = to_csl_json(item)
        assert "arXiv" not in result
        assert "custom" in result
        assert result["custom"]["arXiv"] == "2103.12345"

    def test_real_fixture(self):
        """to_csl_json() on a round-tripped real-world CSL fixture preserves key fields."""
        item = from_csl_json(_FIXTURE_CSL)
        result = to_csl_json(item)
        assert result["id"] == item.citation_key
        assert result["type"] == "article-journal"
        assert result["title"] == _FIXTURE_CSL["title"]
        assert result["DOI"] == _FIXTURE_CSL["DOI"]

    @pytest.mark.parametrize("item_type", ItemType.values)
    def test_round_trip_all_types(self, item_type):
        """Round-trip: export then re-import preserves type for all 45 CSL item types."""
        original = ItemFactory(citation_key=f"RoundTrip_{item_type}", type=item_type)
        exported = to_csl_json(original)
        assert exported["type"] == item_type

        # Re-import under a different key to avoid deduplication
        exported["citation-key"] = f"RoundTrip2_{item_type}"
        reimported = from_csl_json(exported)
        assert reimported.type == item_type

    def test_date_year_only(self, item):
        """to_csl_json() exports year-only PartialDate as [[year]] date-parts."""
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019"))
        result = to_csl_json(item)
        assert result["issued"]["date-parts"] == [[2019]]

    def test_date_year_month(self, item):
        """to_csl_json() exports year-month PartialDate as [[year, month]] date-parts."""
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08"))
        result = to_csl_json(item)
        assert result["issued"]["date-parts"] == [[2019, 8]]

    def test_date_full(self, item):
        """to_csl_json() exports full PartialDate as [[year, month, day]] date-parts."""
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08-16"))
        result = to_csl_json(item)
        assert result["issued"]["date-parts"] == [[2019, 8, 16]]

    def test_date_range(self, item):
        """to_csl_json() exports date range as [[start], [end]] date-parts."""
        ItemDateFactory(
            item=item,
            date_type=DateType.EVENT_DATE,
            begin=PartialDate("2019-08-12"),
            end=PartialDate("2019-08-16"),
        )
        result = to_csl_json(item)
        assert result["event-date"]["date-parts"] == [[2019, 8, 12], [2019, 8, 16]]

    def test_date_with_literal_season_circa(self, item):
        """to_csl_json() exports date literal, season, and circa fields."""
        ItemDateFactory(
            item=item,
            date_type=DateType.ISSUED,
            begin=None,
            literal="Summer 2019",
            season="Summer",
            circa=True,
        )
        result = to_csl_json(item)
        assert result["issued"]["literal"] == "Summer 2019"
        assert result["issued"]["season"] == "Summer"
        assert result["issued"]["circa"] is True

    def test_categories_and_custom_json(self):
        """to_csl_json() exports categories and custom JSONFields directly."""
        item = ItemFactory(
            categories=["physics", "geophysics"],
            custom={"note": "internal reference"},
        )
        result = to_csl_json(item)
        assert result["categories"] == ["physics", "geophysics"]
        assert result["custom"]["note"] == "internal reference"

    def test_name_all_parts(self, item):
        """to_csl_json() exports all name part fields when set."""
        name = NameFactory(
            family="García",
            given="José",
            dropping_particle="de",
            non_dropping_particle="la",
            suffix="Jr.",
            comma_suffix=True,
            static_ordering=True,
            parse_names=True,
        )
        ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR, order=0)
        result = to_csl_json(item)
        author = result["author"][0]
        assert author["family"] == "García"
        assert author.get("dropping-particle") == "de"
        assert author.get("non-dropping-particle") == "la"
        assert author.get("suffix") == "Jr."
        assert author.get("comma-suffix") is True
        assert author.get("static-ordering") is True
        assert author.get("parse-names") is True


@pytest.mark.django_db
class TestFromCslJson:
    """Import from CSL JSON to Item, with validation and deduplication."""

    def test_missing_type_raises(self):
        """from_csl_json() raises ValidationError when 'type' is missing."""
        with pytest.raises(ValidationError, match="type"):
            from_csl_json({"citation-key": "Test2024"})

    def test_unknown_type_raises(self):
        """from_csl_json() raises ValidationError for unknown CSL item type."""
        with pytest.raises(ValidationError, match="Unknown"):
            from_csl_json({"citation-key": "Test2024", "type": "not-a-real-type"})

    def test_missing_both_keys_raises(self):
        """from_csl_json() raises ValidationError when both citation-key and id are absent."""
        with pytest.raises(ValidationError):
            from_csl_json({"type": "article-journal"})

    def test_citation_key_preferred_over_id(self):
        """from_csl_json() uses citation-key over id when both are present."""
        item = from_csl_json({"type": "article-journal", "citation-key": "Preferred2024", "id": "Fallback2024"})
        assert item.citation_key == "Preferred2024"

    def test_falls_back_to_id(self):
        """from_csl_json() falls back to id when citation-key is absent."""
        item = from_csl_json({"type": "article-journal", "id": "FallbackId2024"})
        assert item.citation_key == "FallbackId2024"

    def test_deduplication_appends_b(self):
        """from_csl_json() appends 'b' suffix on first duplicate citation key."""
        ItemFactory(citation_key="Smith2009", type=ItemType.ARTICLE)
        item = from_csl_json({"type": "article-journal", "citation-key": "Smith2009"})
        assert item.citation_key == "Smith2009b"

    def test_deduplication_wrap_around(self):
        """from_csl_json() wraps around from 'z' to 'aa' after 25 suffixed keys."""
        # Create base key and all single-letter suffixes b-z (25 items + 1 base = 26)
        ItemFactory(citation_key="Smith2009", type=ItemType.ARTICLE)
        for ch in "bcdefghijklmnopqrstuvwxyz":
            ItemFactory(citation_key=f"Smith2009{ch}", type=ItemType.ARTICLE)

        item = from_csl_json({"type": "article-journal", "citation-key": "Smith2009"})
        assert item.citation_key == "Smith2009aa"

    def test_date_year_only(self):
        """from_csl_json() imports year-only date-parts correctly."""
        item = from_csl_json(
            {
                "type": "article-journal",
                "citation-key": "Date2024a",
                "issued": {"date-parts": [[2019]]},
            }
        )
        date = ItemDate.objects.get(item=item, date_type=DateType.ISSUED)
        assert date.begin is not None
        assert str(date.begin) == "2019"

    def test_date_year_month(self):
        """from_csl_json() imports year-month date-parts correctly."""
        item = from_csl_json(
            {
                "type": "article-journal",
                "citation-key": "Date2024b",
                "issued": {"date-parts": [[2019, 8]]},
            }
        )
        date = ItemDate.objects.get(item=item, date_type=DateType.ISSUED)
        assert date.begin is not None
        assert str(date.begin).startswith("2019-08")

    def test_date_full(self):
        """from_csl_json() imports full date-parts correctly."""
        item = from_csl_json(
            {
                "type": "article-journal",
                "citation-key": "Date2024c",
                "issued": {"date-parts": [[2019, 8, 16]]},
            }
        )
        date = ItemDate.objects.get(item=item, date_type=DateType.ISSUED)
        assert date.begin is not None
        assert str(date.begin).startswith("2019-08-16")

    def test_date_range(self):
        """from_csl_json() imports date range (begin + end) correctly."""
        item = from_csl_json(
            {
                "type": "article-journal",
                "citation-key": "DateRange2024",
                "event-date": {"date-parts": [[2019, 8, 12], [2019, 8, 16]]},
            }
        )
        date = ItemDate.objects.get(item=item, date_type=DateType.EVENT_DATE)
        assert date.begin is not None
        assert date.end is not None
        assert str(date.begin).startswith("2019-08-12")
        assert str(date.end).startswith("2019-08-16")

    def test_date_raw_fallback(self):
        """from_csl_json() stores raw_date_parts when date-parts are unparseable."""
        unparseable_parts = [["not-a-year"]]
        item = from_csl_json(
            {
                "type": "article-journal",
                "citation-key": "Fallback2024",
                "issued": {"date-parts": unparseable_parts},
            }
        )
        date = ItemDate.objects.get(item=item, date_type=DateType.ISSUED)
        assert date.begin is None
        assert date.raw_date_parts == unparseable_parts

    def test_literal_name(self):
        """from_csl_json() imports literal-only names correctly."""
        item = from_csl_json(
            {
                "type": "article-journal",
                "citation-key": "LiteralName2024",
                "author": [{"literal": "World Health Organization"}],
            }
        )
        item_names = ItemName.objects.filter(item=item, role=NameRole.AUTHOR)
        assert item_names.count() == 1
        assert item_names.first().name.literal == "World Health Organization"

    def test_name_find_or_create(self):
        """from_csl_json() reuses existing Name records for identical name parts."""
        # Import same author twice
        from_csl_json(
            {
                "type": "article-journal",
                "citation-key": "FindOrCreate1",
                "author": [{"family": "Smith", "given": "John"}],
            }
        )
        from_csl_json(
            {
                "type": "article-journal",
                "citation-key": "FindOrCreate2",
                "author": [{"family": "Smith", "given": "John"}],
            }
        )
        # Should have only one Name record for Smith, John
        assert Name.objects.filter(family="Smith", given="John").count() == 1

    def test_deprecated_aliases(self):
        """from_csl_json() handles deprecated shortTitle and event aliases."""
        item = from_csl_json(
            {
                "type": "article-journal",
                "id": "DeprecatedAliasTest",
                "shortTitle": "Short Title",
                "event": "Some Conference",
            }
        )
        assert item.title_short == "Short Title"
        assert item.event_title == "Some Conference"

    def test_unknown_identifier_in_custom(self):
        """from_csl_json() imports unknown identifier type from custom dict."""
        item = from_csl_json(
            {
                "type": "article-journal",
                "id": "CustomIdentifierTest",
                "custom": {"arXiv": "2104.00001"},
            }
        )
        ident = ItemIdentifier.objects.get(item=item, type="arXiv")
        assert ident.value == "2104.00001"

    def test_categories_imported(self):
        """from_csl_json() stores categories JSONField."""
        item = from_csl_json(
            {
                "type": "article-journal",
                "id": "CategoriesTest",
                "categories": ["earth-science", "geophysics"],
            }
        )
        assert item.categories == ["earth-science", "geophysics"]


@pytest.mark.django_db
class TestFromCslJsonList:
    """Batch import with skip-on-error semantics."""

    def test_imports_all_valid(self):
        """from_csl_json_list() returns all successfully imported items."""
        data = [
            {"type": "article-journal", "citation-key": "List1"},
            {"type": "book", "citation-key": "List2"},
            {"type": "thesis", "citation-key": "List3"},
        ]
        items = from_csl_json_list(data)
        assert len(items) == 3

    def test_skips_invalid_items(self):
        """from_csl_json_list() skips invalid items and returns only valid ones."""
        data = [
            {"type": "article-journal", "citation-key": "ValidItem"},
            {"type": "article-journal"},  # missing citation-key and id
            {"citation-key": "MissingType"},  # missing type
        ]
        items = from_csl_json_list(data)
        assert len(items) == 1
        assert items[0].citation_key == "ValidItem"

    def test_unexpected_error_surfaces(self, monkeypatch):
        """from_csl_json_list() lets non-validation errors propagate.

        A bug in the importer (here simulated as a TypeError) must not be
        swallowed and reported as a merely-invalid record. Only ValidationError
        is skipped; everything else surfaces to the caller.
        """
        import literature.converters as converters

        def boom(_item_data):
            raise TypeError("importer bug, not bad input")

        monkeypatch.setattr(converters, "from_csl_json", boom)

        with pytest.raises(TypeError, match="importer bug"):
            from_csl_json_list([{"type": "article-journal", "citation-key": "X"}])


@pytest.mark.django_db
class TestRoundTripFidelity:
    """Full-item round trip: model -> CSL JSON -> model preserves the whole field set.

    SC-002 in spec 001 asks for identical field values across a reference set of
    test fixtures covering all item types and every CSL JSON date form. The
    individual pieces are covered by the classes above (per-form date
    round-trips, name parts, identifier placement, a type-only round-trip over
    all 45 item types, and one real-world fixture), but no single test
    round-trips a fully populated item and asserts the whole field set comes
    back unchanged. This class fills that gap.
    """

    def test_full_item_round_trip_preserves_every_field(self):
        """A fully populated item survives a to_csl_json/from_csl_json cycle."""
        # Every scalar field gets its own field name as the value: short,
        # collision-free, and self-documenting on a mismatch.
        scalar_kwargs = {name: name for name in _item_scalar_field_names()}
        scalar_kwargs["year_suffix"] = "a"  # field name itself overflows max_length=10

        original = ItemFactory(
            citation_key="FullRoundTrip",
            type=ItemType.ARTICLE_JOURNAL,
            categories=["physics", "geophysics"],
            **scalar_kwargs,
        )

        # Contributors across several roles, including a fully detailed name
        # and a literal (organization) name.
        author_one = NameFactory(family="Alpha", given="Ada")
        author_two = NameFactory(family="Beta", given="Bao")
        editor = NameFactory(
            family="García",
            given="José",
            dropping_particle="de",
            non_dropping_particle="la",
            suffix="Jr.",
            comma_suffix=True,
            static_ordering=True,
            parse_names=True,
        )
        translator = NameFactory(family="", given="", literal="World Health Organization")
        ItemNameFactory(item=original, name=author_one, role=NameRole.AUTHOR)
        ItemNameFactory(item=original, name=author_two, role=NameRole.AUTHOR)
        ItemNameFactory(item=original, name=editor, role=NameRole.EDITOR)
        ItemNameFactory(item=original, name=translator, role=NameRole.TRANSLATOR)

        # Every CSL date form, one per date-variable slot: year-only,
        # year-month, full date, full date range, partial date range, and a
        # literal/season/circa date with no date-parts at all.
        ItemDateFactory(item=original, date_type=DateType.ORIGINAL_DATE, begin=PartialDate("2015"))
        ItemDateFactory(item=original, date_type=DateType.ACCESSED, begin=PartialDate("2020-03"))
        ItemDateFactory(item=original, date_type=DateType.ISSUED, begin=PartialDate("2019-08-16"))
        ItemDateFactory(
            item=original,
            date_type=DateType.EVENT_DATE,
            begin=PartialDate("2019-08-12"),
            end=PartialDate("2019-08-16"),
        )
        ItemDateFactory(
            item=original,
            date_type=DateType.AVAILABLE_DATE,
            begin=PartialDate("2021"),
            end=PartialDate("2021-06-30"),
        )
        ItemDateFactory(
            item=original,
            date_type=DateType.SUBMITTED,
            begin=None,
            literal="Summer 2019",
            season="Summer",
            circa=True,
        )

        # A set of identifiers: several known top-level types plus one
        # unknown type routed through the custom object.
        ItemIdentifierFactory(item=original, type=IdentifierType.DOI, value="10.1234/full-round-trip")
        ItemIdentifierFactory(item=original, type=IdentifierType.ISBN, value="978-3-16-148410-0")
        ItemIdentifierFactory(item=original, type=IdentifierType.ISSN, value="0956-540X")
        ItemIdentifierFactory(item=original, type="arXiv", value="2103.12345")

        exported = to_csl_json(original)
        exported["citation-key"] = "FullRoundTrip_reimported"
        reimported = from_csl_json(exported)

        # Scalar fields, plus type and categories.
        for name in _item_scalar_field_names():
            assert getattr(reimported, name) == getattr(original, name), name
        assert reimported.type == original.type
        assert reimported.categories == original.categories

        # Contributors: same roles, same order within each role, same name parts.
        def _name_signature(for_item):
            return [
                (n.role, n.order, n.name.family, n.name.given, n.name.literal)
                for n in ItemName.objects.filter(item=for_item).order_by("role", "order")
            ]

        assert _name_signature(reimported) == _name_signature(original)

        # Dates: same slot, same begin/end/literal/season/circa.
        def _date_signature(for_item):
            return {
                d.date_type: (
                    str(d.begin) if d.begin is not None else None,
                    str(d.end) if d.end is not None else None,
                    d.literal,
                    d.season,
                    d.circa,
                )
                for d in ItemDate.objects.filter(item=for_item)
            }

        assert _date_signature(reimported) == _date_signature(original)

        # Identifiers: same (type, value) set.
        def _identifier_signature(for_item):
            return {(i.type, i.value) for i in ItemIdentifier.objects.filter(item=for_item)}

        assert _identifier_signature(reimported) == _identifier_signature(original)
