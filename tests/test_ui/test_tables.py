"""Tests for ``literature/ui/tables.py``.

Article XIV: one source module, one test module — the per-column split is
expressed with classes, one per column (``TestItemTableMeta`` for the table's
own configuration, ``Test<Column>Column`` per column thereafter).
"""

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.functional import Promise

from literature.choices import DateType, NameRole
from literature.models import Item
from literature.ui.tables import ItemTable
from tests.factories import ItemDateFactory, ItemFactory, ItemNameFactory, NameFactory


def rendered_cell(item, column_name, **table_kwargs):
    """The rendered HTML of one column's cell for one item, without a view."""
    table = ItemTable(Item.objects.filter(pk=item.pk), **table_kwargs)
    row = next(iter(table.rows))
    return row.get_cell(column_name)


def rendered_cell_from_record(item, column_name):
    """Like ``rendered_cell``, but over ``item`` exactly as given — carrying
    whatever attributes (e.g. a ``contributors`` prefetch stand-in) the
    caller already set on it — rather than a fresh copy read back from the
    database."""
    table = ItemTable([item])
    row = next(iter(table.rows))
    return row.get_cell(column_name)


class TestItemTableMeta:
    """The table's own configuration — plan.md D-3."""

    def test_meta_declares_no_model(self):
        # With a model set and no `fields`, django-tables2 generates a
        # column for every model field in addition to the ones declared
        # here — the silent-column problem `fields` being unset is meant to
        # avoid. Column alignment still infers correctly: mvp's
        # `column_alignment_class` reads `table.data.model`, off the
        # queryset itself, never `Meta.model`.
        assert ItemTable._meta.model is None

    def test_meta_uses_the_mvp_bootstrap_template(self):
        # Without this, django-tables2 falls back to its own stock template
        # and none of the mvp column widths, alignment or empty state apply
        # (research R5).
        assert ItemTable._meta.template_name == "django_tables2/bootstrap5-mvp.html"

    def test_meta_empty_text_is_set(self):
        # A flag rather than a displayed string: the mvp template renders its
        # empty state inside `{% if table.empty_text %}` and then shows the
        # view's own empty_state_heading/message instead of this text
        # (research R5, plan.md D-3) — so only truthiness matters here.
        assert ItemTable._meta.empty_text

    def test_meta_default_is_translatable(self):
        # FR-010's empty-value marker, replacing the library's own plain
        # "—" default with a translatable one (plan.md D-3, Article VIII).
        assert isinstance(ItemTable._meta.default, Promise)

    def test_meta_declares_no_order_by(self):
        # An earlier draft named a "created" column that does not exist
        # (FR-002 forbids one) and django-tables2 silently drops an
        # order_by alias it cannot resolve — newest-first comes from
        # Item.Meta.ordering instead (plan.md D-3).
        assert ItemTable._meta.order_by is None

    def test_meta_declares_no_fields(self):
        # Every column is declared explicitly, so a field added to Item
        # later never silently becomes a column (plan.md D-3).
        assert ItemTable._meta.fields is None

    def test_default_order_is_newest_first_through_the_table_not_a_setting(self, db):
        # The table carries no Meta.order_by (above), so this proves the
        # newest-first order a reader sees comes from the queryset's own
        # Item.Meta.ordering, by rendering the table over an unordered
        # queryset rather than by inspecting an absent setting.
        older = ItemFactory(title="Older")
        newer = ItemFactory(title="Newer")
        table = ItemTable(Item.objects.all())
        pks_in_row_order = [row.record.pk for row in table.rows]
        assert pks_in_row_order.index(newer.pk) < pks_in_row_order.index(older.pk)

    def test_declares_the_four_plain_columns_in_order(self):
        assert list(ItemTable.base_columns.keys())[:4] == [
            "citation_key",
            "type",
            "title",
            "container_title",
        ]

    def test_the_short_columns_carry_the_shrink_class_on_both_cell_kinds(self):
        # The project-wide default is no-wrap with no maximum, so an
        # unclassed short column would otherwise be widened by its own
        # heading (plan.md D-5, research amendment to R1).
        for name in ("citation_key", "type"):
            column = ItemTable.base_columns[name]
            assert column.attrs["td"]["class"] == "mvp-col-shrink"
            assert column.attrs["th"]["class"] == "mvp-col-shrink"

    def test_container_title_wraps_with_a_maximum_width(self):
        column = ItemTable.base_columns["container_title"]
        assert column.attrs["td"]["class"] == "mvp-col-wrap mvp-col-max-md"


class TestTitleColumn:
    """The title cell — FR-003, FR-004 (plan.md D-5, research R2/R3)."""

    def test_declares_empty_values_as_empty_tuple(self):
        # Mandatory: without it, an item with title="" never reaches
        # render_title, defeating the fallback chain in exactly the case it
        # exists for (research R3).
        assert ItemTable.base_columns["title"].empty_values == ()

    def test_shows_the_items_own_title(self, db):
        item = ItemFactory(title="A Direct Title")
        assert "A Direct Title" in rendered_cell(item, "title")

    def test_falls_back_to_short_title_when_no_title(self, db):
        item = ItemFactory(title="", title_short="Short Form")
        assert "Short Form" in rendered_cell(item, "title")

    def test_falls_back_to_original_title_when_no_title_or_short_title(self, db):
        item = ItemFactory(title="", title_short="", original_title="Original Form")
        assert "Original Form" in rendered_cell(item, "title")

    def test_falls_back_to_volume_title_when_earlier_rungs_are_all_absent(self, db):
        item = ItemFactory(title="", title_short="", original_title="", volume_title="Volume Form")
        assert "Volume Form" in rendered_cell(item, "title")

    def test_falls_back_to_the_citation_key_when_the_item_carries_no_title_at_all(self, db):
        item = ItemFactory(title="", title_short="", original_title="", volume_title="", citation_key="FallbackKey2026")
        assert "FallbackKey2026" in rendered_cell(item, "title")

    def test_links_to_the_items_own_detail_page(self, db):
        item = ItemFactory(title="A Linked Title")
        content = rendered_cell(item, "title")
        assert f'href="{reverse("literature:item-detail", kwargs={"pk": item.pk})}"' in content

    def test_link_carries_the_hover_underline_classes(self, db):
        item = ItemFactory(title="A Followable Title")
        content = rendered_cell(item, "title")
        assert 'class="link link-hover"' in content


class TestTypeColumn:
    """The item-type cell — FR-005, FR-017 (plan.md D-5, research R3)."""

    def test_orders_on_the_stored_type_value(self):
        # Sorting by item type follows the stored CSL type rather than the
        # translated label, which cannot be done in the database (FR-017).
        assert ItemTable.base_columns["type"].order_by == ("type",)

    def test_shows_the_translated_label_rather_than_the_stored_value(self, db):
        from literature.choices import ItemType

        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        content = rendered_cell(item, "type")
        assert "Journal Article" in content
        assert "article-journal" not in content


class TestContributorsColumn:
    """The credited-names cell — FR-006 through FR-008 (plan.md D-6, research R9)."""

    def test_declares_empty_values_as_empty_tuple(self):
        # The column resolves to nothing at all — Item has no "contributors"
        # field — so without this the marker would render even when the
        # prefetch carries names (research R3).
        assert ItemTable.base_columns["contributors"].empty_values == ()

    def test_is_not_orderable(self):
        # Assembled from a through-model across two roles with no single
        # value to order on (FR-015).
        assert ItemTable.base_columns["contributors"].orderable is False

    def test_lists_author_role_contributors_in_stored_order(self, db):
        item = ItemFactory()
        first = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        second = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        item.contributors = [first, second]
        content = rendered_cell_from_record(item, "contributors")
        assert content.index(str(first.name)) < content.index(str(second.name))

    def test_falls_back_to_editors_when_there_are_no_authors(self, db):
        item = ItemFactory()
        editor = ItemNameFactory(item=item, role=NameRole.EDITOR)
        item.contributors = [editor]
        content = rendered_cell_from_record(item, "contributors")
        assert str(editor.name) in content

    def test_ignores_editors_when_authors_are_present(self, db):
        item = ItemFactory()
        author = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        editor = ItemNameFactory(item=item, role=NameRole.EDITOR)
        item.contributors = [author, editor]
        content = rendered_cell_from_record(item, "contributors")
        assert str(author.name) in content
        assert str(editor.name) not in content

    def test_no_contributors_at_all_renders_the_empty_value_marker(self, db):
        item = ItemFactory()
        item.contributors = []
        content = rendered_cell_from_record(item, "contributors")
        assert "—" in content

    def test_exactly_three_names_shows_no_and_others_suffix(self, db):
        item = ItemFactory()
        names = [ItemNameFactory(item=item, role=NameRole.AUTHOR) for _ in range(3)]
        item.contributors = names
        content = rendered_cell_from_record(item, "contributors")
        for item_name in names:
            assert str(item_name.name) in content
        assert "other" not in content

    def test_more_than_three_names_shows_the_first_three_and_the_count_of_the_rest(self, db):
        item = ItemFactory()
        names = [ItemNameFactory(item=item, role=NameRole.AUTHOR) for _ in range(5)]
        item.contributors = names
        content = rendered_cell_from_record(item, "contributors")
        for item_name in names[:3]:
            assert str(item_name.name) in content
        for item_name in names[3:]:
            assert str(item_name.name) not in content
        assert "2" in content

    def test_each_name_links_to_its_contributor_page(self, db):
        item = ItemFactory()
        item_name = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        item.contributors = [item_name]
        content = rendered_cell_from_record(item, "contributors")
        contributor_url = reverse("literature:contributor-detail", kwargs={"pk": item_name.name.pk})
        assert f'href="{contributor_url}"' in content

    def test_a_name_containing_markup_renders_escaped(self, db):
        item = ItemFactory()
        contributor = NameFactory(family="<script>alert(1)</script>", given="")
        item_name = ItemNameFactory(item=item, name=contributor, role=NameRole.AUTHOR)
        item.contributors = [item_name]
        content = rendered_cell_from_record(item, "contributors")
        assert "<script>" not in content
        assert "&lt;script&gt;" in content

    def test_a_record_carrying_no_contributors_attribute_degrades_rather_than_raising(self, db):
        # research R9 — a record drawn through a plain SingleTableView with
        # no prefetch has no "contributors" attribute at all.
        item = ItemFactory()
        content = rendered_cell(item, "contributors")
        assert "—" in content

    def test_never_touches_the_manager(self, db):
        item = ItemFactory()
        ItemNameFactory(item=item, role=NameRole.AUTHOR)
        item.contributors = []
        with CaptureQueriesContext(connection) as queries:
            rendered_cell_from_record(item, "contributors")
        assert len(queries.captured_queries) == 0


class TestIssuedColumn:
    """The issued cell — FR-009 (plan.md D-7, research R8)."""

    def test_declares_empty_values_as_empty_tuple(self):
        assert ItemTable.base_columns["issued"].empty_values == ()

    def test_ships_unsortable_until_the_annotation_lands(self):
        # The annotation and order_issued that make the sort resolvable do
        # not land until US-3 (T017/T018); a header advertising a sort
        # before then raises FieldError on the package's default page.
        assert ItemTable.base_columns["issued"].orderable is False

    def test_year_only_precision_shows_the_year_without_inventing_a_month_or_day(self, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="1998")
        content = rendered_cell(item, "issued")
        assert "1998" in content
        assert "1998-01-01" not in content

    def test_full_date_precision(self, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="1998-03-14")
        assert "1998-03-14" in rendered_cell(item, "issued")

    def test_a_range_shows_both_ends(self, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2019", end="2021")
        content = rendered_cell(item, "issued")
        assert "2019" in content
        assert "2021" in content

    def test_a_free_text_literal_date(self, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=None, literal="in press")
        assert "in press" in rendered_cell(item, "issued")

    def test_no_issued_date_at_all_renders_the_empty_value_marker(self, db):
        # Edge case: the item's only date is "accessed" (FR-010).
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2020")
        content = rendered_cell(item, "issued")
        assert "—" in content

    def test_ignores_a_non_issued_date_slot(self, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2020")
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2019")
        content = rendered_cell(item, "issued")
        assert "2019" in content


class TestActionsColumn:
    """The row's edit control — FR-019, FR-020 (plan.md D-5, research R6)."""

    def test_is_not_orderable(self):
        # A control, not data — no single value to order on (FR-015). Also
        # what earns the column its centred alignment (research R6).
        assert ItemTable.base_columns["actions"].orderable is False

    def test_verbose_name_is_empty(self):
        assert ItemTable.base_columns["actions"].verbose_name == ""

    def test_uses_the_table_actions_template(self):
        assert ItemTable.base_columns["actions"].template_name == "literature/ui/_table_actions.html"

    def test_links_to_the_records_own_update_page(self, db):
        item = ItemFactory()
        content = rendered_cell(item, "actions")
        update_url = reverse("literature:item-update", kwargs={"pk": item.pk})
        assert f'href="{update_url}"' in content

    def test_each_row_links_to_its_own_record_not_a_shared_one(self, db):
        first = ItemFactory()
        second = ItemFactory()
        first_content = rendered_cell(first, "actions")
        second_content = rendered_cell(second, "actions")
        assert reverse("literature:item-update", kwargs={"pk": first.pk}) in first_content
        assert reverse("literature:item-update", kwargs={"pk": second.pk}) not in first_content
        assert reverse("literature:item-update", kwargs={"pk": second.pk}) in second_content

    def test_shown_by_default(self, db):
        # A bare ItemTable (no show_update_action passed at all) is open —
        # this feature introduces no access control of its own (FR-020).
        item = ItemFactory()
        content = rendered_cell(item, "actions")
        assert "href=" in content

    def test_hidden_when_show_update_action_is_false(self, db):
        # The same show_update_action mechanism ItemDetailView's own edit
        # action reads — set here directly rather than through a view, to
        # prove the column itself honours the flag (FR-020).
        item = ItemFactory()
        content = rendered_cell(item, "actions", show_update_action=False)
        update_url = reverse("literature:item-update", kwargs={"pk": item.pk})
        assert f'href="{update_url}"' not in content
