"""Tests for literature.converters module (US2 — Convert Between Model and CSL JSON).

Tests cover contract from contracts/csl-json.md:
- to_csl_json(): serialization guarantees, blank field omission, name ordering,
  identifier placement, fixture round-trip, parametrized type round-trips
- from_csl_json(): validation errors, citation-key resolution, deduplication,
  date round-trips, literal names, unknown identifiers
- from_csl_json_list(): batch import with skip-on-error semantics
"""

import json
import os

import pytest
from django.core.exceptions import ValidationError
from partial_date import PartialDate

from literature.choices import DateType, IdentifierType, ItemType, NameRole
from literature.converters import from_csl_json, from_csl_json_list, to_csl_json

# Load the real-world fixture
_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "data", "publication-csl.json")
with open(_FIXTURE_PATH) as _f:
    _FIXTURE_CSL = json.load(_f)


# ---------------------------------------------------------------------------
# to_csl_json() tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_to_csl_json_always_has_id_and_type(make_item):
    """to_csl_json() output always has 'id' and 'type' keys."""
    item = make_item(citation_key="Test2024", type=ItemType.BOOK)
    result = to_csl_json(item)
    assert "id" in result
    assert result["id"] == "Test2024"
    assert "type" in result
    assert result["type"] == ItemType.BOOK


@pytest.mark.django_db
def test_to_csl_json_omits_blank_fields(make_item):
    """to_csl_json() omits blank/null optional fields."""
    item = make_item(citation_key="Minimal2024", type=ItemType.ARTICLE)
    result = to_csl_json(item)
    assert "abstract" not in result
    assert "title" not in result
    assert "publisher" not in result


@pytest.mark.django_db
def test_to_csl_json_includes_non_blank_fields(make_item):
    """to_csl_json() includes non-blank fields with correct CSL JSON keys."""
    from literature.models import Item

    item = Item.objects.create(
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


@pytest.mark.django_db
def test_to_csl_json_name_arrays_ordered(make_item):
    """to_csl_json() exports name arrays in order."""
    from literature.models import ItemName, Name

    item = make_item()
    n1 = Name.objects.create(family="Alpha", given="A")
    n2 = Name.objects.create(family="Beta", given="B")
    n3 = Name.objects.create(family="Gamma", given="G")
    ItemName.objects.create(item=item, name=n1, role=NameRole.AUTHOR, order=0)
    ItemName.objects.create(item=item, name=n2, role=NameRole.AUTHOR, order=1)
    ItemName.objects.create(item=item, name=n3, role=NameRole.AUTHOR, order=2)
    result = to_csl_json(item)
    assert "author" in result
    assert [a["family"] for a in result["author"]] == ["Alpha", "Beta", "Gamma"]


@pytest.mark.django_db
def test_to_csl_json_known_identifier_as_top_level_key(make_item):
    """to_csl_json() places known identifiers as top-level CSL JSON keys."""
    from literature.models import ItemIdentifier

    item = make_item()
    ItemIdentifier.objects.create(item=item, type=IdentifierType.DOI, value="10.1234/test")
    ItemIdentifier.objects.create(item=item, type=IdentifierType.ISSN, value="0956-540X")
    result = to_csl_json(item)
    assert result["DOI"] == "10.1234/test"
    assert result["ISSN"] == "0956-540X"


@pytest.mark.django_db
def test_to_csl_json_unknown_identifier_in_custom(make_item):
    """to_csl_json() places unknown identifier types in the custom object."""
    from literature.models import ItemIdentifier

    item = make_item()
    ItemIdentifier.objects.create(item=item, type="arXiv", value="2103.12345")
    result = to_csl_json(item)
    assert "arXiv" not in result
    assert "custom" in result
    assert result["custom"]["arXiv"] == "2103.12345"


@pytest.mark.django_db
def test_to_csl_json_real_fixture():
    """to_csl_json() on a round-tripped real-world CSL fixture preserves key fields."""
    item = from_csl_json(_FIXTURE_CSL)
    result = to_csl_json(item)
    assert result["id"] == item.citation_key
    assert result["type"] == "article-journal"
    assert result["title"] == _FIXTURE_CSL["title"]
    assert result["DOI"] == _FIXTURE_CSL["DOI"]


@pytest.mark.django_db
@pytest.mark.parametrize("item_type", ItemType.values)
def test_to_csl_json_round_trip_all_types(item_type):
    """Round-trip: export then re-import preserves type for all 45 CSL item types."""
    from literature.models import Item

    original = Item.objects.create(citation_key=f"RoundTrip_{item_type}", type=item_type)
    exported = to_csl_json(original)
    assert exported["type"] == item_type

    # Re-import under a different key to avoid deduplication
    exported["citation-key"] = f"RoundTrip2_{item_type}"
    reimported = from_csl_json(exported)
    assert reimported.type == item_type


# ---------------------------------------------------------------------------
# to_csl_json() date serialization
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_to_csl_json_date_year_only(make_item):
    """to_csl_json() exports year-only PartialDate as [[year]] date-parts."""
    from literature.models import ItemDate

    item = make_item()
    ItemDate.objects.create(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019"))
    result = to_csl_json(item)
    assert result["issued"]["date-parts"] == [[2019]]


@pytest.mark.django_db
def test_to_csl_json_date_year_month(make_item):
    """to_csl_json() exports year-month PartialDate as [[year, month]] date-parts."""
    from literature.models import ItemDate

    item = make_item()
    ItemDate.objects.create(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08"))
    result = to_csl_json(item)
    assert result["issued"]["date-parts"] == [[2019, 8]]


@pytest.mark.django_db
def test_to_csl_json_date_full(make_item):
    """to_csl_json() exports full PartialDate as [[year, month, day]] date-parts."""
    from literature.models import ItemDate

    item = make_item()
    ItemDate.objects.create(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08-16"))
    result = to_csl_json(item)
    assert result["issued"]["date-parts"] == [[2019, 8, 16]]


@pytest.mark.django_db
def test_to_csl_json_date_range(make_item):
    """to_csl_json() exports date range as [[start], [end]] date-parts."""
    from literature.models import ItemDate

    item = make_item()
    ItemDate.objects.create(
        item=item,
        date_type=DateType.EVENT_DATE,
        begin=PartialDate("2019-08-12"),
        end=PartialDate("2019-08-16"),
    )
    result = to_csl_json(item)
    assert result["event-date"]["date-parts"] == [[2019, 8, 12], [2019, 8, 16]]


# ---------------------------------------------------------------------------
# from_csl_json() validation errors
# ---------------------------------------------------------------------------


def test_from_csl_json_missing_type_raises():
    """from_csl_json() raises ValidationError when 'type' is missing."""
    with pytest.raises(ValidationError, match="type"):
        from_csl_json({"citation-key": "Test2024"})


def test_from_csl_json_unknown_type_raises():
    """from_csl_json() raises ValidationError for unknown CSL item type."""
    with pytest.raises(ValidationError, match="Unknown"):
        from_csl_json({"citation-key": "Test2024", "type": "not-a-real-type"})


def test_from_csl_json_missing_both_keys_raises():
    """from_csl_json() raises ValidationError when both citation-key and id are absent."""
    with pytest.raises(ValidationError):
        from_csl_json({"type": "article-journal"})


@pytest.mark.django_db
def test_from_csl_json_citation_key_preferred_over_id():
    """from_csl_json() uses citation-key over id when both are present."""
    item = from_csl_json({"type": "article-journal", "citation-key": "Preferred2024", "id": "Fallback2024"})
    assert item.citation_key == "Preferred2024"


@pytest.mark.django_db
def test_from_csl_json_falls_back_to_id():
    """from_csl_json() falls back to id when citation-key is absent."""
    item = from_csl_json({"type": "article-journal", "id": "FallbackId2024"})
    assert item.citation_key == "FallbackId2024"


# ---------------------------------------------------------------------------
# from_csl_json() citation key deduplication
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_from_csl_json_deduplication_appends_b():
    """from_csl_json() appends 'b' suffix on first duplicate citation key."""
    from literature.models import Item

    Item.objects.create(citation_key="Smith2009", type=ItemType.ARTICLE)
    item = from_csl_json({"type": "article-journal", "citation-key": "Smith2009"})
    assert item.citation_key == "Smith2009b"


@pytest.mark.django_db
def test_from_csl_json_deduplication_wrap_around():
    """from_csl_json() wraps around from 'z' to 'aa' after 25 suffixed keys."""
    from literature.models import Item

    # Create base key and all single-letter suffixes b-z (25 items + 1 base = 26)
    Item.objects.create(citation_key="Smith2009", type=ItemType.ARTICLE)
    for ch in "bcdefghijklmnopqrstuvwxyz":
        Item.objects.create(citation_key=f"Smith2009{ch}", type=ItemType.ARTICLE)

    item = from_csl_json({"type": "article-journal", "citation-key": "Smith2009"})
    assert item.citation_key == "Smith2009aa"


# ---------------------------------------------------------------------------
# from_csl_json() date round-trips
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_from_csl_json_date_year_only():
    """from_csl_json() imports year-only date-parts correctly."""
    from literature.models import ItemDate

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


@pytest.mark.django_db
def test_from_csl_json_date_year_month():
    """from_csl_json() imports year-month date-parts correctly."""
    from literature.models import ItemDate

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


@pytest.mark.django_db
def test_from_csl_json_date_full():
    """from_csl_json() imports full date-parts correctly."""
    from literature.models import ItemDate

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


@pytest.mark.django_db
def test_from_csl_json_date_range():
    """from_csl_json() imports date range (begin + end) correctly."""
    from literature.models import ItemDate

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


@pytest.mark.django_db
def test_from_csl_json_date_raw_fallback():
    """from_csl_json() stores raw_date_parts when date-parts are unparseable."""
    from literature.models import ItemDate

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


# ---------------------------------------------------------------------------
# from_csl_json() name handling
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_from_csl_json_literal_name():
    """from_csl_json() imports literal-only names correctly."""
    from literature.models import ItemName

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


@pytest.mark.django_db
def test_from_csl_json_name_find_or_create():
    """from_csl_json() reuses existing Name records for identical name parts."""
    from literature.models import Name

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


# ---------------------------------------------------------------------------
# from_csl_json_list() batch import
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_from_csl_json_list_imports_all_valid():
    """from_csl_json_list() returns all successfully imported items."""
    data = [
        {"type": "article-journal", "citation-key": "List1"},
        {"type": "book", "citation-key": "List2"},
        {"type": "thesis", "citation-key": "List3"},
    ]
    items = from_csl_json_list(data)
    assert len(items) == 3


@pytest.mark.django_db
def test_from_csl_json_list_skips_invalid_items():
    """from_csl_json_list() skips invalid items and returns only valid ones."""
    data = [
        {"type": "article-journal", "citation-key": "ValidItem"},
        {"type": "article-journal"},  # missing citation-key and id
        {"citation-key": "MissingType"},  # missing type
    ]
    items = from_csl_json_list(data)
    assert len(items) == 1
    assert items[0].citation_key == "ValidItem"


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_to_csl_json_date_with_literal_season_circa(make_item):
    """to_csl_json() exports date literal, season, and circa fields."""
    from literature.models import ItemDate

    item = make_item()
    ItemDate.objects.create(
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


@pytest.mark.django_db
def test_to_csl_json_categories_and_custom_json(make_item):
    """to_csl_json() exports categories and custom JSONFields directly."""
    item = make_item(
        categories=["physics", "geophysics"],
        custom={"note": "internal reference"},
    )
    result = to_csl_json(item)
    assert result["categories"] == ["physics", "geophysics"]
    assert result["custom"]["note"] == "internal reference"


@pytest.mark.django_db
def test_to_csl_json_name_all_parts(make_item, make_name):
    """to_csl_json() exports all name part fields when set."""
    from literature.models import ItemName

    item = make_item()
    name = make_name(
        family="García",
        given="José",
        dropping_particle="de",
        non_dropping_particle="la",
        suffix="Jr.",
        comma_suffix=True,
        static_ordering=True,
        parse_names=True,
    )
    ItemName.objects.create(item=item, name=name, role=NameRole.AUTHOR, order=0)
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
def test_from_csl_json_deprecated_aliases(make_item):
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


@pytest.mark.django_db
def test_from_csl_json_unknown_identifier_in_custom():
    """from_csl_json() imports unknown identifier type from custom dict."""
    from literature.models import ItemIdentifier

    item = from_csl_json(
        {
            "type": "article-journal",
            "id": "CustomIdentifierTest",
            "custom": {"arXiv": "2104.00001"},
        }
    )
    ident = ItemIdentifier.objects.get(item=item, type="arXiv")
    assert ident.value == "2104.00001"


@pytest.mark.django_db
def test_from_csl_json_categories_imported():
    """from_csl_json() stores categories JSONField."""
    item = from_csl_json(
        {
            "type": "article-journal",
            "id": "CategoriesTest",
            "categories": ["earth-science", "geophysics"],
        }
    )
    assert item.categories == ["earth-science", "geophysics"]
