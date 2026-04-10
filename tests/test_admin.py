"""Tests for the literature Django admin interface.

Covers:
- US1: Item changelist, add, and change views; fieldset headings; list columns
- US2: Contributor inline visibility and ordering controls
- US3: ItemDate and ItemIdentifier inline sections
- US4: Search and sidebar filters (type, publisher, year)
"""

import pytest
from django.test import Client

# ---------------------------------------------------------------------------
# US1: Item admin — changelist, add, change views
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_item_changelist_returns_200(admin_user):
    """Item changelist URL returns HTTP 200 (T010 US1)."""
    client = Client()
    client.force_login(admin_user)
    response = client.get("/admin/literature/item/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_item_add_returns_200(admin_user):
    """Item add URL returns HTTP 200 (T010 US1)."""
    client = Client()
    client.force_login(admin_user)
    response = client.get("/admin/literature/item/add/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_item_change_returns_200(admin_user, make_item):
    """Item change URL returns HTTP 200 for a saved item (T010 US1)."""
    item = make_item(title="Test Title")
    client = Client()
    client.force_login(admin_user)
    response = client.get(f"/admin/literature/item/{item.pk}/change/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_item_changelist_contains_expected_columns(admin_user, make_item):
    """Item changelist response contains citation key column header (T010 US1)."""
    make_item(title="Sample Article", citation_key="SampleKey")
    client = Client()
    client.force_login(admin_user)
    response = client.get("/admin/literature/item/")
    content = response.content.decode()
    assert "citation" in content.lower()


@pytest.mark.django_db
def test_item_change_form_contains_fieldset_headings(admin_user, make_item):
    """Item change form response contains expected fieldset headings (T010 US1)."""
    item = make_item(title="Test Title")
    client = Client()
    client.force_login(admin_user)
    response = client.get(f"/admin/literature/item/{item.pk}/change/")
    content = response.content.decode()
    assert "Identity" in content
    assert "Titles" in content
    assert "Publication" in content


# ---------------------------------------------------------------------------
# US2: Contributor inline (T014)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_item_change_form_contains_contributor_inline(admin_user, make_item):
    """Item change form contains the contributor inline management form (T014 US2)."""
    item = make_item(title="Test Title")
    client = Client()
    client.force_login(admin_user)
    response = client.get(f"/admin/literature/item/{item.pk}/change/")
    content = response.content.decode()
    assert "item_names-TOTAL_FORMS" in content


@pytest.mark.django_db
def test_item_change_form_contains_ordering_controls(admin_user, make_item):
    """Item change form contains ordering controls for contributors (T014 US2)."""
    item = make_item(title="Test Title")
    client = Client()
    client.force_login(admin_user)
    response = client.get(f"/admin/literature/item/{item.pk}/change/")
    content = response.content.decode()
    # OrderedTabularInline renders move_up_down_links in the form
    assert "move-up" in content or "move_up" in content


@pytest.mark.django_db
def test_post_item_saves_contributor(admin_user, make_item, make_name):
    """POST to item change URL with contributor data saves a new ItemName (T014 US2)."""
    from literature.choices import NameRole
    from literature.models import ItemName

    item = make_item(title="Test Title")
    name = make_name(family="Doe", given="Jane")
    client = Client()
    client.force_login(admin_user)

    post_data = {
        "citation_key": item.citation_key,
        "type": item.type,
        "item_names-TOTAL_FORMS": "1",
        "item_names-INITIAL_FORMS": "0",
        "item_names-MIN_NUM_FORMS": "0",
        "item_names-MAX_NUM_FORMS": "1000",
        "item_names-0-name": str(name.pk),
        "item_names-0-role": NameRole.AUTHOR,
        "item_names-0-id": "",
        "item_names-0-item": str(item.pk),
        "item_dates-TOTAL_FORMS": "0",
        "item_dates-INITIAL_FORMS": "0",
        "item_dates-MIN_NUM_FORMS": "0",
        "item_dates-MAX_NUM_FORMS": "1000",
        "item_identifiers-TOTAL_FORMS": "0",
        "item_identifiers-INITIAL_FORMS": "0",
        "item_identifiers-MIN_NUM_FORMS": "0",
        "item_identifiers-MAX_NUM_FORMS": "1000",
        "_save": "Save",
    }
    response = client.post(f"/admin/literature/item/{item.pk}/change/", data=post_data)
    assert response.status_code in (200, 302)
    assert ItemName.objects.filter(item=item, name=name, role=NameRole.AUTHOR).exists()


@pytest.mark.django_db
def test_saved_contributor_reappears_on_item_form(admin_user, make_item_name):
    """Reopening the item shows the saved contributor (T014 US2)."""
    item_name = make_item_name()
    client = Client()
    client.force_login(admin_user)
    response = client.get(f"/admin/literature/item/{item_name.item.pk}/change/")
    content = response.content.decode()
    assert str(item_name.name.family) in content


# ---------------------------------------------------------------------------
# US3: Date and identifier inlines (T018)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_item_change_form_contains_date_inline(admin_user, make_item):
    """Item change form contains the date inline management form (T018 US3)."""
    item = make_item(title="Test Title")
    client = Client()
    client.force_login(admin_user)
    response = client.get(f"/admin/literature/item/{item.pk}/change/")
    content = response.content.decode()
    assert "item_dates-TOTAL_FORMS" in content


@pytest.mark.django_db
def test_item_change_form_contains_identifier_inline(admin_user, make_item):
    """Item change form contains the identifier inline management form (T018 US3)."""
    item = make_item(title="Test Title")
    client = Client()
    client.force_login(admin_user)
    response = client.get(f"/admin/literature/item/{item.pk}/change/")
    content = response.content.decode()
    assert "item_identifiers-TOTAL_FORMS" in content


@pytest.mark.django_db
def test_post_item_saves_date(admin_user, make_item):
    """POST with ItemDate data saves a related ItemDate record (T018 US3)."""
    from literature.choices import DateType
    from literature.models import ItemDate

    item = make_item(title="Test Title")
    client = Client()
    client.force_login(admin_user)

    post_data = {
        "citation_key": item.citation_key,
        "type": item.type,
        "item_names-TOTAL_FORMS": "0",
        "item_names-INITIAL_FORMS": "0",
        "item_names-MIN_NUM_FORMS": "0",
        "item_names-MAX_NUM_FORMS": "1000",
        "item_dates-TOTAL_FORMS": "1",
        "item_dates-INITIAL_FORMS": "0",
        "item_dates-MIN_NUM_FORMS": "0",
        "item_dates-MAX_NUM_FORMS": "1000",
        "item_dates-0-id": "",
        "item_dates-0-item": str(item.pk),
        "item_dates-0-date_type": DateType.ISSUED,
        "item_dates-0-begin": "2024",
        "item_dates-0-end": "",
        "item_dates-0-season": "",
        "item_dates-0-circa": "",
        "item_dates-0-literal": "",
        "item_dates-0-raw": "",
        "item_identifiers-TOTAL_FORMS": "0",
        "item_identifiers-INITIAL_FORMS": "0",
        "item_identifiers-MIN_NUM_FORMS": "0",
        "item_identifiers-MAX_NUM_FORMS": "1000",
        "_save": "Save",
    }
    response = client.post(f"/admin/literature/item/{item.pk}/change/", data=post_data)
    assert response.status_code in (200, 302)
    assert ItemDate.objects.filter(item=item, date_type=DateType.ISSUED).exists()


@pytest.mark.django_db
def test_post_item_saves_identifier(admin_user, make_item):
    """POST with ItemIdentifier data saves a related ItemIdentifier record (T018 US3)."""
    from literature.choices import IdentifierType
    from literature.models import ItemIdentifier

    item = make_item(title="Test Title")
    client = Client()
    client.force_login(admin_user)

    post_data = {
        "citation_key": item.citation_key,
        "type": item.type,
        "item_names-TOTAL_FORMS": "0",
        "item_names-INITIAL_FORMS": "0",
        "item_names-MIN_NUM_FORMS": "0",
        "item_names-MAX_NUM_FORMS": "1000",
        "item_dates-TOTAL_FORMS": "0",
        "item_dates-INITIAL_FORMS": "0",
        "item_dates-MIN_NUM_FORMS": "0",
        "item_dates-MAX_NUM_FORMS": "1000",
        "item_identifiers-TOTAL_FORMS": "1",
        "item_identifiers-INITIAL_FORMS": "0",
        "item_identifiers-MIN_NUM_FORMS": "0",
        "item_identifiers-MAX_NUM_FORMS": "1000",
        "item_identifiers-0-id": "",
        "item_identifiers-0-item": str(item.pk),
        "item_identifiers-0-type": IdentifierType.DOI,
        "item_identifiers-0-value": "10.1234/test",
        "_save": "Save",
    }
    response = client.post(f"/admin/literature/item/{item.pk}/change/", data=post_data)
    assert response.status_code in (200, 302)
    assert ItemIdentifier.objects.filter(item=item, value="10.1234/test").exists()


# ---------------------------------------------------------------------------
# US4: Search and sidebar filters (T024)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_item_changelist_search_filters_by_title(admin_user, make_item):
    """Changelist search returns only matching items (T024 US4)."""
    make_item(title="Quantum Physics", citation_key="QP2024")
    make_item(title="Biology Basics", citation_key="BB2024")
    client = Client()
    client.force_login(admin_user)
    response = client.get("/admin/literature/item/?q=Quantum")
    content = response.content.decode()
    assert "Quantum" in content
    assert "Biology" not in content


@pytest.mark.django_db
def test_item_changelist_type_filter(admin_user, make_item):
    """Changelist type filter returns only matching items (T024 US4)."""
    from literature.choices import ItemType

    make_item(title="Journal Article", citation_key="JA2024", type=ItemType.ARTICLE_JOURNAL)
    make_item(title="A Book", citation_key="BK2024", type=ItemType.BOOK)
    client = Client()
    client.force_login(admin_user)
    response = client.get(f"/admin/literature/item/?type={ItemType.ARTICLE_JOURNAL}")
    content = response.content.decode()
    assert "Journal Article" in content
    assert "A Book" not in content


@pytest.mark.django_db
def test_item_changelist_year_filter(admin_user, make_item, make_item_date):
    """Changelist year filter returns only items with the given issued year (T024 US4)."""
    from partial_date import PartialDate

    item_2024 = make_item(title="Article 2024", citation_key="A2024")
    item_2020 = make_item(title="Article 2020", citation_key="A2020")
    make_item_date(item=item_2024, begin=PartialDate("2024"))
    make_item_date(item=item_2020, begin=PartialDate("2020"))
    client = Client()
    client.force_login(admin_user)
    response = client.get("/admin/literature/item/?issued_year=2024")
    content = response.content.decode()
    assert "Article 2024" in content
    assert "Article 2020" not in content


@pytest.mark.django_db
def test_year_filter_sidebar_contains_year_entries(admin_user, make_item, make_item_date):
    """Year filter sidebar contains entries for years with at least one issued date (T024 US4)."""
    from partial_date import PartialDate

    item = make_item(title="Year Test", citation_key="YT2024")
    make_item_date(item=item, begin=PartialDate("2022"))
    client = Client()
    client.force_login(admin_user)
    response = client.get("/admin/literature/item/")
    content = response.content.decode()
    assert "2022" in content


# ---------------------------------------------------------------------------
# US5: Name admin (T029)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_name_changelist_returns_200(admin_user, make_name):
    """Name changelist URL returns HTTP 200 (T029 US5)."""
    make_name(family="Doe", given="John")
    client = Client()
    client.force_login(admin_user)
    response = client.get("/admin/literature/name/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_name_changelist_search_filters_by_family(admin_user, make_name):
    """Name changelist search by family name returns only matching names (T029 US5)."""
    make_name(family="Anderson", given="Alice")
    make_name(family="Baker", given="Bob")
    client = Client()
    client.force_login(admin_user)
    response = client.get("/admin/literature/name/?q=Anderson")
    content = response.content.decode()
    assert "Anderson" in content
    assert "Baker" not in content


@pytest.mark.django_db
def test_name_change_returns_200(admin_user, make_name):
    """Name change URL returns HTTP 200 for a saved Name (T029 US5)."""
    name = make_name(family="Smith", given="Jane")
    client = Client()
    client.force_login(admin_user)
    response = client.get(f"/admin/literature/name/{name.pk}/change/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_post_name_change_persists(admin_user, make_name):
    """POST to Name change URL with updated given field persists the change (T029 US5)."""
    name = make_name(family="Smith", given="Jane")
    client = Client()
    client.force_login(admin_user)
    data = {
        "family": "Smith",
        "given": "Janet",
        "literal": "",
        "dropping_particle": "",
        "non_dropping_particle": "",
        "suffix": "",
        "_save": "Save",
    }
    response = client.post(f"/admin/literature/name/{name.pk}/change/", data)
    assert response.status_code == 302
    name.refresh_from_db()
    assert name.given == "Janet"
