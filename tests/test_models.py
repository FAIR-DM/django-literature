"""Tests for the literature models (US1 — Store and Retrieve Bibliographic Entries).

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
from literature.models import Item, ItemDate, ItemIdentifier, ItemName, Name
from tests.factories import ItemDateFactory, ItemFactory, ItemIdentifierFactory, ItemNameFactory, NameFactory


@pytest.mark.django_db
class TestItemModel:
    """Item CRUD, optional-field persistence, and __str__ behaviour."""

    @pytest.mark.parametrize("item_type", ItemType.values)
    def test_crud_all_types(self, item_type):
        """Item can be created and retrieved for every CSL item type."""
        citation_key = f"TestKey2024_{item_type}"
        item = ItemFactory(citation_key=citation_key, type=item_type)
        retrieved = Item.objects.get(pk=item.pk)
        assert retrieved.citation_key == citation_key
        assert retrieved.type == item_type

    def test_required_fields_only(self):
        """Item can be created with only citation_key and type."""
        item = ItemFactory(citation_key="Minimal2024", type=ItemType.ARTICLE_JOURNAL)
        assert item.pk is not None

    def test_optional_fields_persist(self):
        """Item optional fields are stored and retrieved correctly."""
        item = ItemFactory(
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

    def test_str_returns_citation_key(self):
        """Item.__str__ returns the citation key when no title is set."""
        item = ItemFactory(citation_key="CiteKey2024", type=ItemType.ARTICLE)
        assert str(item) == "CiteKey2024"
        assert len(str(item)) > 0

    def test_str_returns_title_when_set(self):
        """Item.__str__ returns the title when it is set (T006)."""
        item = ItemFactory(citation_key="CiteKey2024", type=ItemType.ARTICLE, title="A Short Title")
        assert str(item) == "A Short Title"

    def test_str_fallback_to_citation_key(self):
        """Item.__str__ falls back to citation_key when title is empty (T006)."""
        item = ItemFactory(citation_key="FallbackKey", type=ItemType.BOOK, title="")
        assert str(item) == "FallbackKey"

    def test_str_truncates_long_title(self):
        """Item.__str__ truncates titles over 80 characters with an ellipsis (T006)."""
        long_title = "A" * 81
        item = ItemFactory(citation_key="LongTitle2024", type=ItemType.BOOK, title=long_title)
        result = str(item)
        assert result == "A" * 80 + "…"
        assert len(result) == 81  # 80 chars + 1 ellipsis char

    def test_auto_timestamps_set_on_creation(self):
        """Item auto-timestamps are set on creation."""
        item = ItemFactory(citation_key="Auto2024", type=ItemType.REPORT)
        assert item.created is not None
        assert item.modified is not None


@pytest.mark.django_db
class TestNameModel:
    """Name field persistence and __str__ fallbacks."""

    def test_all_parts_persist(self):
        """Name model stores all name parts correctly."""
        name = NameFactory(
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

    def test_literal_only(self):
        """Name can be created with only the literal field (institutional name)."""
        name = NameFactory(family="", given="", literal="World Health Organization")
        retrieved = Name.objects.get(pk=name.pk)
        assert retrieved.literal == "World Health Organization"
        assert retrieved.family == ""
        assert retrieved.given == ""

    def test_str_family_given(self):
        """Name.__str__ returns 'family, given' when both are set."""
        name = NameFactory(family="Smith", given="John")
        result = str(name)
        assert len(result) > 0
        assert "Smith" in result

    def test_str_family_given_format(self):
        """Name.__str__ returns 'Family, Given' format when family name is present (T006b)."""
        name = NameFactory(family="Smith", given="John")
        assert str(name) == "Smith, John"

    def test_str_family_only(self):
        """Name.__str__ returns family name alone when given is absent (T006b)."""
        name = NameFactory(family="Smith", given="")
        assert str(name) == "Smith"

    def test_str_literal_fallback(self):
        """Name.__str__ returns literal when family and given are absent (T006b)."""
        name = NameFactory(family="", given="", literal="Harvard University")
        assert str(name) == "Harvard University"

    def test_str_pk_fallback(self):
        """Name.__str__ returns 'Name #<pk>' as last fallback (T006b)."""
        name = NameFactory(family="", given="", literal="")
        assert str(name) == f"Name #{name.pk}"

    def test_str_literal_only(self):
        """Name.__str__ returns the literal when family/given are empty."""
        name = NameFactory(family="", given="", literal="World Health Organization")
        result = str(name)
        assert len(result) > 0
        assert "World Health Organization" in result


@pytest.mark.django_db
class TestItemNameModel:
    """ItemName through-model role, uniqueness, and ordering."""

    def test_records_role(self, item, name):
        """ItemName records the role correctly."""
        item_name = ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR)
        assert item_name.role == NameRole.AUTHOR

    def test_unique_constraint(self, item, name):
        """ItemName enforces uniqueness of (item, role, name)."""
        ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR)
        with pytest.raises(Exception):  # IntegrityError on duplicate
            ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR)

    def test_multiple_roles_same_name(self, item, name):
        """Same name can have different roles on the same item."""
        ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=name, role=NameRole.EDITOR)
        assert ItemName.objects.filter(item=item, name=name).count() == 2

    def test_ordering_preserved(self, item):
        """ItemName preserves order_with_respect_to=(item, role)."""
        n1 = NameFactory(family="First", given="A")
        n2 = NameFactory(family="Second", given="B")
        n3 = NameFactory(family="Third", given="C")
        ItemNameFactory(item=item, name=n1, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=n2, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=n3, role=NameRole.AUTHOR)
        ordered = list(ItemName.objects.filter(item=item, role=NameRole.AUTHOR).order_by("order"))
        assert [in_.name.family for in_ in ordered] == ["First", "Second", "Third"]

    def test_str_non_empty(self, item, name):
        """ItemName.__str__ returns a non-empty string."""
        item_name = ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR)
        assert len(str(item_name)) > 0


@pytest.mark.django_db
class TestItemDateModel:
    """ItemDate partial-date storage, uniqueness, and auxiliary fields."""

    def test_year_only(self, item):
        """ItemDate stores a year-only partial date via begin field."""
        item_date = ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019"))
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin) == "2019"

    def test_year_month(self, item):
        """ItemDate stores a year+month partial date."""
        item_date = ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08"))
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08")

    def test_full_date(self, item):
        """ItemDate stores a full date."""
        item_date = ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08-16"))
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08-16")

    def test_range(self, item):
        """ItemDate stores a date range via begin and end fields."""
        item_date = ItemDateFactory(
            item=item,
            date_type=DateType.EVENT_DATE,
            begin=PartialDate("2019-08-12"),
            end=PartialDate("2019-08-16"),
        )
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08-12")
        assert str(retrieved.end).startswith("2019-08-16")

    def test_unique_constraint(self, item):
        """ItemDate enforces uniqueness of (item, date_type)."""
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019"))
        with pytest.raises(Exception):  # IntegrityError on duplicate
            ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2020"))

    def test_str_non_empty(self, item):
        """ItemDate.__str__ returns a non-empty string."""
        item_date = ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08-16"))
        assert len(str(item_date)) > 0

    def test_all_fields(self, item):
        """ItemDate stores all auxiliary fields: season, circa, literal, raw, raw_date_parts."""
        item_date = ItemDateFactory(
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


@pytest.mark.django_db
class TestItemIdentifierModel:
    """ItemIdentifier storage for known and unknown identifier types."""

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
    def test_known_types(self, item, identifier_type, value):
        """ItemIdentifier stores all 6 known identifier types correctly."""
        ident = ItemIdentifierFactory(item=item, type=identifier_type, value=value)
        retrieved = ItemIdentifier.objects.get(pk=ident.pk)
        assert retrieved.type == identifier_type
        assert retrieved.value == value

    def test_unknown_type(self, item):
        """ItemIdentifier accepts unknown identifier type strings (FR-017)."""
        ident = ItemIdentifierFactory(item=item, type="arXiv", value="2103.12345")
        retrieved = ItemIdentifier.objects.get(pk=ident.pk)
        assert retrieved.type == "arXiv"
        assert retrieved.value == "2103.12345"

    def test_unique_constraint(self, item):
        """ItemIdentifier enforces uniqueness of (item, type)."""
        ItemIdentifierFactory(item=item, type=IdentifierType.DOI, value="10.1/first")
        with pytest.raises(Exception):  # IntegrityError on duplicate
            ItemIdentifierFactory(item=item, type=IdentifierType.DOI, value="10.1/second")

    def test_str_non_empty(self, item):
        """ItemIdentifier.__str__ returns a non-empty string."""
        ident = ItemIdentifierFactory(item=item, type=IdentifierType.DOI, value="10.1234/test")
        assert len(str(ident)) > 0
