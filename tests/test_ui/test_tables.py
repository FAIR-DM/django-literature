"""Tests for ``literature/ui/tables.py``.

Article XIV: one source module, one test module — the per-column split is
expressed with classes, one per column (``TestItemTableMeta`` for the table's
own configuration, ``Test<Column>Column`` per column thereafter).
"""

from django.urls import reverse
from django.utils.functional import Promise

from literature.models import Item
from literature.ui.tables import ItemTable
from tests.factories import ItemFactory


def rendered_cell(item, column_name):
    """The rendered HTML of one column's cell for one item, without a view."""
    table = ItemTable(Item.objects.filter(pk=item.pk))
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
