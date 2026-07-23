"""Tests for literature models (US1 — Store and Retrieve Bibliographic Entries).

Tests cover:
- Item CRUD across all 45 CSL item types
- Name model field persistence including literal-only records
- ItemName through-model role and ordering
- ItemDate storage for all date forms (year-only, year-month, full, range)
- ItemIdentifier storage for all 6 known types and unknown types
- Model __str__ methods returning non-empty strings
- UniqueConstraint enforcement
"""

import pytest
from partial_date import PartialDate

from literature.choices import DateType, IdentifierType, ItemType, NameRole

# ---------------------------------------------------------------------------
# Item CRUD — parametrized across all 45 CSL item types
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("item_type", ItemType.values)
def test_item_crud_all_types(item_type):
    """Item can be created and retrieved for every CSL item type."""
    from literature.models import Item

    citation_key = f"TestKey2024_{item_type}"
    item = Item.objects.create(citation_key=citation_key, type=item_type)
    retrieved = Item.objects.get(pk=item.pk)
    assert retrieved.citation_key == citation_key
    assert retrieved.type == item_type


@pytest.mark.django_db
def test_item_required_fields_only():
    """Item can be created with only citation_key and type."""
    from literature.models import Item

    item = Item.objects.create(citation_key="Minimal2024", type=ItemType.ARTICLE_JOURNAL)
    assert item.pk is not None


@pytest.mark.django_db
def test_item_optional_fields_persist():
    """Item optional fields are stored and retrieved correctly."""
    from literature.models import Item

    item = Item.objects.create(
        citation_key="Full2024",
        type=ItemType.BOOK,
        title="The Full Book",
        title_short="Full Book",
        abstract="An abstract.",
        publisher="Test Publisher",
        publisher_place="Test City",
        volume="2",
        issue="3",
        page="100-200",
        language="en",
        keyword="science, research",
        categories=["cat1", "cat2"],
        custom={"extra": "value"},
    )
    retrieved = Item.objects.get(pk=item.pk)
    assert retrieved.title == "The Full Book"
    assert retrieved.title_short == "Full Book"
    assert retrieved.abstract == "An abstract."
    assert retrieved.publisher == "Test Publisher"
    assert retrieved.publisher_place == "Test City"
    assert retrieved.volume == "2"
    assert retrieved.issue == "3"
    assert retrieved.page == "100-200"
    assert retrieved.language == "en"
    assert retrieved.keyword == "science, research"
    assert retrieved.categories == ["cat1", "cat2"]
    assert retrieved.custom == {"extra": "value"}


@pytest.mark.django_db
def test_item_str_returns_citation_key():
    """Item.__str__ returns the citation key."""
    from literature.models import Item

    item = Item.objects.create(citation_key="CiteKey2024", type=ItemType.ARTICLE)
    assert str(item) == "CiteKey2024"
    assert len(str(item)) > 0


@pytest.mark.django_db
def test_item_str_returns_title_when_set():
    """Item.__str__ returns the title when it is set (T006)."""
    from literature.models import Item

    item = Item.objects.create(citation_key="CiteKey2024", type=ItemType.ARTICLE, title="A Short Title")
    assert str(item) == "A Short Title"


@pytest.mark.django_db
def test_item_str_fallback_to_citation_key():
    """Item.__str__ falls back to citation_key when title is empty (T006)."""
    from literature.models import Item

    item = Item.objects.create(citation_key="FallbackKey", type=ItemType.BOOK, title="")
    assert str(item) == "FallbackKey"


@pytest.mark.django_db
def test_item_str_truncates_long_title():
    """Item.__str__ truncates titles over 80 characters with an ellipsis (T006)."""
    from literature.models import Item

    long_title = "A" * 81
    item = Item.objects.create(citation_key="LongTitle2024", type=ItemType.BOOK, title=long_title)
    result = str(item)
    assert result == "A" * 80 + "…"
    assert len(result) == 81  # 80 chars + 1 ellipsis char

    """Item auto-timestamps are set on creation."""
    from literature.models import Item

    item = Item.objects.create(citation_key="Auto2024", type=ItemType.REPORT)
    assert item.created is not None
    assert item.modified is not None


# ---------------------------------------------------------------------------
# Name model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_name_all_parts_persist():
    """Name model stores all name parts correctly."""
    from literature.models import Name

    name = Name.objects.create(
        family="Smith",
        given="John A.",
        dropping_particle="von",
        non_dropping_particle="de",
        suffix="Jr.",
        literal="",
        comma_suffix=True,
        static_ordering=False,
        parse_names=True,
    )
    retrieved = Name.objects.get(pk=name.pk)
    assert retrieved.family == "Smith"
    assert retrieved.given == "John A."
    assert retrieved.dropping_particle == "von"
    assert retrieved.non_dropping_particle == "de"
    assert retrieved.suffix == "Jr."
    assert retrieved.comma_suffix is True
    assert retrieved.static_ordering is False
    assert retrieved.parse_names is True


@pytest.mark.django_db
def test_name_literal_only():
    """Name can be created with only the literal field (institutional name)."""
    from literature.models import Name

    name = Name.objects.create(literal="World Health Organization")
    retrieved = Name.objects.get(pk=name.pk)
    assert retrieved.literal == "World Health Organization"
    assert retrieved.family == ""
    assert retrieved.given == ""


@pytest.mark.django_db
def test_name_str_family_given():
    """Name.__str__ returns 'family, given' when both are set."""
    from literature.models import Name

    name = Name.objects.create(family="Smith", given="John")
    result = str(name)
    assert len(result) > 0
    assert "Smith" in result


@pytest.mark.django_db
def test_name_str_family_given_format():
    """Name.__str__ returns 'Family, Given' format when family name is present (T006b)."""
    from literature.models import Name

    name = Name.objects.create(family="Smith", given="John")
    assert str(name) == "Smith, John"


@pytest.mark.django_db
def test_name_str_family_only():
    """Name.__str__ returns family name alone when given is absent (T006b)."""
    from literature.models import Name

    name = Name.objects.create(family="Smith", given="")
    assert str(name) == "Smith"


@pytest.mark.django_db
def test_name_str_literal_fallback():
    """Name.__str__ returns literal when family and given are absent (T006b)."""
    from literature.models import Name

    name = Name.objects.create(family="", given="", literal="Harvard University")
    assert str(name) == "Harvard University"


@pytest.mark.django_db
def test_name_str_pk_fallback():
    """Name.__str__ returns 'Name #<pk>' as last fallback (T006b)."""
    from literature.models import Name

    name = Name.objects.create(family="", given="", literal="")
    assert str(name) == f"Name #{name.pk}"


@pytest.mark.django_db
def test_name_str_literal_only():
    """Name.__str__ returns the literal when family/given are empty."""
    from literature.models import Name

    name = Name.objects.create(literal="World Health Organization")
    result = str(name)
    assert len(result) > 0
    assert "World Health Organization" in result


# ---------------------------------------------------------------------------
# ItemName through-model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_item_name_records_role(make_item, make_name):
    """ItemName records the role correctly."""
    from literature.models import ItemName

    item = make_item()
    name = make_name()
    item_name = ItemName.objects.create(item=item, name=name, role=NameRole.AUTHOR)
    assert item_name.role == NameRole.AUTHOR


@pytest.mark.django_db
def test_item_name_unique_constraint(make_item, make_name):
    """ItemName enforces uniqueness of (item, role, name)."""
    from literature.models import ItemName

    item = make_item()
    name = make_name()
    ItemName.objects.create(item=item, name=name, role=NameRole.AUTHOR)
    with pytest.raises(Exception):  # IntegrityError on duplicate
        ItemName.objects.create(item=item, name=name, role=NameRole.AUTHOR)


@pytest.mark.django_db
def test_item_name_multiple_roles_same_name(make_item, make_name):
    """Same name can have different roles on the same item."""
    from literature.models import ItemName

    item = make_item()
    name = make_name()
    ItemName.objects.create(item=item, name=name, role=NameRole.AUTHOR)
    ItemName.objects.create(item=item, name=name, role=NameRole.EDITOR)
    assert ItemName.objects.filter(item=item, name=name).count() == 2


@pytest.mark.django_db
def test_item_name_ordering_preserved(make_item, make_name):
    """ItemName preserves order_with_respect_to=(item, role)."""
    from literature.models import ItemName, Name

    item = make_item()
    n1 = Name.objects.create(family="First", given="A")
    n2 = Name.objects.create(family="Second", given="B")
    n3 = Name.objects.create(family="Third", given="C")
    ItemName.objects.create(item=item, name=n1, role=NameRole.AUTHOR)
    ItemName.objects.create(item=item, name=n2, role=NameRole.AUTHOR)
    ItemName.objects.create(item=item, name=n3, role=NameRole.AUTHOR)
    ordered = list(ItemName.objects.filter(item=item, role=NameRole.AUTHOR).order_by("order"))
    assert [in_.name.family for in_ in ordered] == ["First", "Second", "Third"]


@pytest.mark.django_db
def test_item_name_str_non_empty(make_item, make_name):
    """ItemName.__str__ returns a non-empty string."""
    from literature.models import ItemName

    item = make_item()
    name = make_name()
    item_name = ItemName.objects.create(item=item, name=name, role=NameRole.AUTHOR)
    assert len(str(item_name)) > 0


# ---------------------------------------------------------------------------
# ItemDate — year-only, year-month, full date, date range
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_item_date_year_only(make_item):
    """ItemDate stores a year-only partial date via begin field."""
    from literature.models import ItemDate

    item = make_item()
    item_date = ItemDate.objects.create(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019"))
    retrieved = ItemDate.objects.get(pk=item_date.pk)
    assert str(retrieved.begin) == "2019"


@pytest.mark.django_db
def test_item_date_year_month(make_item):
    """ItemDate stores a year+month partial date."""
    from literature.models import ItemDate

    item = make_item()
    item_date = ItemDate.objects.create(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08"))
    retrieved = ItemDate.objects.get(pk=item_date.pk)
    assert str(retrieved.begin).startswith("2019-08")


@pytest.mark.django_db
def test_item_date_full_date(make_item):
    """ItemDate stores a full date."""
    from literature.models import ItemDate

    item = make_item()
    item_date = ItemDate.objects.create(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08-16"))
    retrieved = ItemDate.objects.get(pk=item_date.pk)
    assert str(retrieved.begin).startswith("2019-08-16")


@pytest.mark.django_db
def test_item_date_range(make_item):
    """ItemDate stores a date range via begin and end fields."""
    from literature.models import ItemDate

    item = make_item()
    item_date = ItemDate.objects.create(
        item=item,
        date_type=DateType.EVENT_DATE,
        begin=PartialDate("2019-08-12"),
        end=PartialDate("2019-08-16"),
    )
    retrieved = ItemDate.objects.get(pk=item_date.pk)
    assert str(retrieved.begin).startswith("2019-08-12")
    assert str(retrieved.end).startswith("2019-08-16")


@pytest.mark.django_db
def test_item_date_unique_constraint(make_item):
    """ItemDate enforces uniqueness of (item, date_type)."""
    from literature.models import ItemDate

    item = make_item()
    ItemDate.objects.create(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019"))
    with pytest.raises(Exception):  # IntegrityError on duplicate
        ItemDate.objects.create(item=item, date_type=DateType.ISSUED, begin=PartialDate("2020"))


@pytest.mark.django_db
def test_item_date_str_non_empty(make_item):
    """ItemDate.__str__ returns a non-empty string."""
    from literature.models import ItemDate

    item = make_item()
    item_date = ItemDate.objects.create(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08-16"))
    assert len(str(item_date)) > 0


@pytest.mark.django_db
def test_item_date_all_fields(make_item):
    """ItemDate stores all auxiliary fields: season, circa, literal, raw, raw_date_parts."""
    from literature.models import ItemDate

    item = make_item()
    item_date = ItemDate.objects.create(
        item=item,
        date_type=DateType.SUBMITTED,
        season="1",
        circa=True,
        literal="Spring 2019",
        raw="2019 spring",
        raw_date_parts=[[2019]],
    )
    retrieved = ItemDate.objects.get(pk=item_date.pk)
    assert retrieved.season == "1"
    assert retrieved.circa is True
    assert retrieved.literal == "Spring 2019"
    assert retrieved.raw == "2019 spring"
    assert retrieved.raw_date_parts == [[2019]]


# ---------------------------------------------------------------------------
# ItemIdentifier
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "identifier_type,value",
    [
        (IdentifierType.DOI, "10.1093/gji/ggz376"),
        (IdentifierType.ISBN, "978-3-16-148410-0"),
        (IdentifierType.ISSN, "0956-540X"),
        (IdentifierType.PMID, "19482853"),
        (IdentifierType.PMCID, "PMC2728067"),
        (IdentifierType.URL, "https://example.com/article"),
    ],
)
def test_item_identifier_known_types(make_item, identifier_type, value):
    """ItemIdentifier stores all 6 known identifier types correctly."""
    from literature.models import ItemIdentifier

    item = make_item()
    ident = ItemIdentifier.objects.create(item=item, type=identifier_type, value=value)
    retrieved = ItemIdentifier.objects.get(pk=ident.pk)
    assert retrieved.type == identifier_type
    assert retrieved.value == value


@pytest.mark.django_db
def test_item_identifier_unknown_type(make_item):
    """ItemIdentifier accepts unknown identifier type strings (FR-017)."""
    from literature.models import ItemIdentifier

    item = make_item()
    ident = ItemIdentifier.objects.create(item=item, type="arXiv", value="2103.12345")
    retrieved = ItemIdentifier.objects.get(pk=ident.pk)
    assert retrieved.type == "arXiv"
    assert retrieved.value == "2103.12345"


@pytest.mark.django_db
def test_item_identifier_unique_constraint(make_item):
    """ItemIdentifier enforces uniqueness of (item, type)."""
    from literature.models import ItemIdentifier

    item = make_item()
    ItemIdentifier.objects.create(item=item, type=IdentifierType.DOI, value="10.1/first")
    with pytest.raises(Exception):  # IntegrityError on duplicate
        ItemIdentifier.objects.create(item=item, type=IdentifierType.DOI, value="10.1/second")


@pytest.mark.django_db
def test_item_identifier_str_non_empty(make_item):
    """ItemIdentifier.__str__ returns a non-empty string."""
    from literature.models import ItemIdentifier

    item = make_item()
    ident = ItemIdentifier.objects.create(item=item, type=IdentifierType.DOI, value="10.1234/test")
    assert len(str(ident)) > 0
