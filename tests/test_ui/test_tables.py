"""Tests for ``literature/ui/tables.py``.

The testing standard (§4): one source module, one test module — the per-column split is
expressed with classes, one per column (``TestItemTableMeta`` for the table's
own configuration, ``Test<Column>Column`` per column thereafter).
"""

import re

import pytest
from django.db import connection
from django.db.models import OuterRef, Subquery
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.functional import Promise

from literature.choices import DateType, NameRole
from literature.importers.results import Outcome
from literature.models import Item, ItemDate
from literature.ui.importing import ImportReportRow
from literature.ui.tables import ImportReportTable, ItemTable
from tests.factories import ItemDateFactory, ItemFactory, ItemNameFactory, NameFactory


def issued_annotated_queryset():
    """Return items carrying the ``issued`` annotation ``ItemTableView`` builds, without a view."""
    issued_begin = ItemDate.objects.filter(
        item=OuterRef("pk"), date_type=DateType.ISSUED
    ).values("begin")[:1]
    return Item.objects.annotate(issued=Subquery(issued_begin))


def rendered_cell(item, column_name, **table_kwargs):
    """The rendered HTML of one column's cell for one item, without a view."""
    table = ItemTable(Item.objects.filter(pk=item.pk), **table_kwargs)
    row = next(iter(table.rows))
    return row.get_cell(column_name)


def rendered_cell_from_record(item, column_name):
    """Render like ``rendered_cell``, but over ``item`` as given rather than re-read."""
    table = ItemTable([item])
    row = next(iter(table.rows))
    return row.get_cell(column_name)


class TestItemTableMeta:
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
        # and none of the mvp column widths, alignment or empty state apply.
        assert ItemTable._meta.template_name == "django_tables2/bootstrap5-mvp.html"

    def test_meta_empty_text_is_set(self):
        # A flag rather than a displayed string: the mvp template renders its
        # empty state inside `{% if table.empty_text %}` and then shows the
        # view's own empty_state_heading/message instead of this text
        # — so only truthiness matters here.
        assert ItemTable._meta.empty_text

    def test_meta_default_is_translatable(self):
        # Replaces the library's own plain "—" default with a translatable one
        # (Article VIII).
        assert isinstance(ItemTable._meta.default, Promise)

    def test_meta_declares_no_order_by(self):
        # An earlier draft named a "created" column that does not exist
        # and django-tables2 silently drops an
        # order_by alias it cannot resolve — newest-first comes from
        # Item.Meta.ordering instead.
        assert ItemTable._meta.order_by is None

    def test_meta_declares_no_fields(self):
        # Every column is declared explicitly, so a field added to Item
        # later never silently becomes a column.
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
        # heading.
        for name in ("citation_key", "type"):
            column = ItemTable.base_columns[name]
            assert column.attrs["td"]["class"] == "mvp-col-shrink"
            assert column.attrs["th"]["class"] == "mvp-col-shrink"

    def test_container_title_wraps_with_a_maximum_width(self):
        column = ItemTable.base_columns["container_title"]
        assert column.attrs["td"]["class"] == "mvp-col-wrap mvp-col-max-md"


class TestTitleColumn:
    def test_declares_empty_values_as_empty_tuple(self):
        # Mandatory: without it, an item with title="" never reaches
        # render_title, defeating the fallback chain in exactly the case it
        # exists for.
        assert ItemTable.base_columns["title"].empty_values == ()

    def test_shows_the_items_own_title(self, db):
        item = ItemFactory(title="A Direct Title")
        assert "A Direct Title" in rendered_cell(item, "title")

    def test_a_title_containing_markup_renders_escaped(self, db):
        # The title cell is the one place a Python renderer's return value
        # reaches the page, and a title is free text entered through this
        # package's own open write pages. The escaping is the linkify
        # wrapper's, which is a library detail — pinned here so a later
        # switch to a template column, or a mark_safe, fails rather than
        # passing every other test in this class.
        item = ItemFactory(title="<script>alert(1)</script>")
        content = rendered_cell(item, "title")
        assert "<script>" not in content
        assert "&lt;script&gt;" in content

    def test_falls_back_to_short_title_when_no_title(self, db):
        item = ItemFactory(title="", title_short="Short Form")
        assert "Short Form" in rendered_cell(item, "title")

    def test_falls_back_to_original_title_when_no_title_or_short_title(self, db):
        item = ItemFactory(title="", title_short="", original_title="Original Form")
        assert "Original Form" in rendered_cell(item, "title")

    def test_falls_back_to_volume_title_when_earlier_rungs_are_all_absent(self, db):
        item = ItemFactory(
            title="", title_short="", original_title="", volume_title="Volume Form"
        )
        assert "Volume Form" in rendered_cell(item, "title")

    def test_falls_back_to_the_citation_key_when_the_item_carries_no_title_at_all(
        self, db
    ):
        item = ItemFactory(
            title="",
            title_short="",
            original_title="",
            volume_title="",
            citation_key="FallbackKey2026",
        )
        assert "FallbackKey2026" in rendered_cell(item, "title")

    def test_links_to_the_items_own_detail_page(self, db):
        item = ItemFactory(title="A Linked Title")
        content = rendered_cell(item, "title")
        assert (
            f'href="{reverse("literature:item-detail", kwargs={"pk": item.pk})}"'
            in content
        )


class TestTypeColumn:
    def test_orders_on_the_stored_type_value(self):
        # Sorting by item type follows the stored CSL type rather than the
        # translated label, which cannot be done in the database.
        assert ItemTable.base_columns["type"].order_by == ("type", "pk")

    def test_shows_the_translated_label_rather_than_the_stored_value(self, db):
        from literature.choices import ItemType

        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        content = rendered_cell(item, "type")
        assert str(ItemType.ARTICLE_JOURNAL.label) in content
        assert "article-journal" not in content


class TestContributorsColumn:
    def test_declares_empty_values_as_empty_tuple(self):
        # The column resolves to nothing at all — Item has no "contributors"
        # field — so without this the marker would render even when the
        # prefetch carries names.
        assert ItemTable.base_columns["contributors"].empty_values == ()

    def test_is_not_orderable(self):
        # Assembled from a through-model across two roles with no single
        # value to order on.
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

    def test_more_than_three_names_shows_the_first_three_and_the_count_of_the_rest(
        self, db
    ):
        item = ItemFactory()
        names = [ItemNameFactory(item=item, role=NameRole.AUTHOR) for _ in range(5)]
        item.contributors = names
        content = rendered_cell_from_record(item, "contributors")
        for item_name in names[:3]:
            assert str(item_name.name) in content
        for item_name in names[3:]:
            assert str(item_name.name) not in content
        # The whole phrase, not the bare count: the three rendered links
        # already carry a "2" in a contributor URL and in a factory-built
        # name, so asserting the digit alone stays green with the overflow
        # indication deleted outright.
        assert "and 2 others" in content

    def test_exactly_one_name_beyond_the_first_three_reads_in_the_singular(self, db):
        item = ItemFactory()
        item.contributors = [
            ItemNameFactory(item=item, role=NameRole.AUTHOR) for _ in range(4)
        ]
        content = rendered_cell_from_record(item, "contributors")
        assert "and 1 other" in content
        assert "others" not in content

    def test_each_name_links_to_its_contributor_page(self, db):
        item = ItemFactory()
        item_name = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        item.contributors = [item_name]
        content = rendered_cell_from_record(item, "contributors")
        contributor_url = reverse(
            "literature:contributor-detail", kwargs={"pk": item_name.name.pk}
        )
        assert f'href="{contributor_url}"' in content

    def test_a_name_containing_markup_renders_escaped(self, db):
        item = ItemFactory()
        contributor = NameFactory(family="<script>alert(1)</script>", given="")
        item_name = ItemNameFactory(item=item, name=contributor, role=NameRole.AUTHOR)
        item.contributors = [item_name]
        content = rendered_cell_from_record(item, "contributors")
        assert "<script>" not in content
        assert "&lt;script&gt;" in content

    def test_a_record_carrying_no_contributors_attribute_degrades_rather_than_raising(
        self, db
    ):
        # A record drawn through a plain SingleTableView with
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
    def test_declares_empty_values_as_empty_tuple(self):
        assert ItemTable.base_columns["issued"].empty_values == ()

    def test_is_orderable_now_the_annotation_and_order_issued_exist(self, db):
        # Shipped unsortable (an explicit orderable=False), because a
        # header advertising a sort before the annotation existed raised
        # FieldError on the package's default page. That override is gone —
        # the column's own orderable is the library's default (None, "auto")
        # — and the issued annotation plus order_issued (below) resolve
        # the sort, so a bound table now reports the column as orderable.
        assert ItemTable.base_columns["issued"].orderable is None
        table = ItemTable(issued_annotated_queryset())
        assert table.columns["issued"].orderable is True

    def test_year_only_precision_shows_the_year_without_inventing_a_month_or_day(
        self, db
    ):
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
        ItemDateFactory(
            item=item, date_type=DateType.ISSUED, begin=None, literal="in press"
        )
        assert "in press" in rendered_cell(item, "issued")

    def test_no_issued_date_at_all_renders_the_empty_value_marker(self, db):
        # Edge case: the item's only date is "accessed".
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
    def test_is_not_orderable(self):
        # A control, not data — no single value to order on. Also
        # what earns the column its centred alignment.
        assert ItemTable.base_columns["actions"].orderable is False

    def test_verbose_name_is_empty(self):
        assert ItemTable.base_columns["actions"].verbose_name == ""

    def test_uses_the_table_actions_template(self):
        assert (
            ItemTable.base_columns["actions"].template_name
            == "literature/ui/table_actions.html"
        )

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
        assert (
            reverse("literature:item-update", kwargs={"pk": first.pk}) in first_content
        )
        assert (
            reverse("literature:item-update", kwargs={"pk": second.pk})
            not in first_content
        )
        assert (
            reverse("literature:item-update", kwargs={"pk": second.pk})
            in second_content
        )

    def test_shown_by_default(self, db):
        # A bare ItemTable (no show_update_action passed at all) is open —
        # this feature introduces no access control of its own.
        item = ItemFactory()
        content = rendered_cell(item, "actions")
        assert "href=" in content

    def test_hidden_when_show_update_action_is_false(self, db):
        # The same show_update_action mechanism ItemDetailView's own edit
        # action reads — set here directly rather than through a view, to
        # prove the column itself honours the flag.
        item = ItemFactory()
        content = rendered_cell(item, "actions", show_update_action=False)
        update_url = reverse("literature:item-update", kwargs={"pk": item.pk})
        assert f'href="{update_url}"' not in content


class TestEverySortIsTotal:
    # Asserted on the emitted SQL: SQLite's stable scan hides a missing tiebreak that
    # paginated PostgreSQL queries expose.

    SORTABLE = ["citation_key", "type", "title", "container_title"]

    @pytest.mark.parametrize("column_name", SORTABLE)
    @pytest.mark.parametrize("direction", ["", "-"])
    def test_the_sort_ends_on_the_primary_key(self, db, column_name, direction):
        ItemFactory.create_batch(2, **{column_name: "the same value"})
        table = ItemTable(Item.objects.all(), order_by=f"{direction}{column_name}")
        with CaptureQueriesContext(connection) as queries:
            list(table.rows)
        order_by_clause = queries.captured_queries[0]["sql"].split("ORDER BY")[-1]
        assert re.search(r'"id"\s*(ASC|DESC)?\s*$', order_by_clause), order_by_clause

    @pytest.mark.parametrize("direction", ["", "-"])
    def test_the_issued_sort_ends_on_the_primary_key_too(self, db, direction):
        for _ in range(2):
            item = ItemFactory()
            ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        table = ItemTable(issued_annotated_queryset(), order_by=f"{direction}issued")
        with CaptureQueriesContext(connection) as queries:
            list(table.rows)
        order_by_clause = queries.captured_queries[0]["sql"].split("ORDER BY")[-1]
        assert re.search(r'"id"\s*(ASC|DESC)?\s*$', order_by_clause), order_by_clause


class TestIssuedOrdering:
    # SQLite and PostgreSQL place NULLs differently, so the order is stated in code.

    def test_declares_order_by_issued(self):
        assert ItemTable.base_columns["issued"].order_by == ("issued",)
        # The primary-key tiebreak for this column is added by order_issued
        # rather than declared here — see TestEverySortIsTotal.

    def test_ascending_order_places_an_undated_reference_last(self, db):
        dated = ItemFactory(citation_key="Dated")
        ItemDateFactory(item=dated, date_type=DateType.ISSUED, begin="2020")
        undated = ItemFactory(citation_key="Undated")
        table = ItemTable(issued_annotated_queryset(), order_by="issued")
        pks_in_row_order = [row.record.pk for row in table.rows]
        assert pks_in_row_order[-1] == undated.pk
        assert pks_in_row_order[0] == dated.pk

    def test_descending_order_also_places_an_undated_reference_last(self, db):
        # nulls_last applies in both directions — a naive
        # "-issued" would otherwise put the undated reference first on the
        # reverse of the ascending case.
        dated = ItemFactory(citation_key="Dated")
        ItemDateFactory(item=dated, date_type=DateType.ISSUED, begin="2020")
        undated = ItemFactory(citation_key="Undated")
        table = ItemTable(issued_annotated_queryset(), order_by="-issued")
        pks_in_row_order = [row.record.pk for row in table.rows]
        assert pks_in_row_order[-1] == undated.pk
        assert pks_in_row_order[0] == dated.pk

    def test_descending_order_places_the_most_recent_issued_date_first(self, db):
        older = ItemFactory(citation_key="Older")
        ItemDateFactory(item=older, date_type=DateType.ISSUED, begin="2010")
        newer = ItemFactory(citation_key="Newer")
        ItemDateFactory(item=newer, date_type=DateType.ISSUED, begin="2020")
        table = ItemTable(issued_annotated_queryset(), order_by="-issued")
        pks_in_row_order = [row.record.pk for row in table.rows]
        assert pks_in_row_order.index(newer.pk) < pks_in_row_order.index(older.pk)


#: Declaration order of ``ImportReportTable``'s columns — how its one
#: rendered row's ``<td>`` cells line up below.
IMPORT_REPORT_COLUMNS = ["position", "citation_key", "outcome", "reason"]


def import_report_cell(rows, column_name):
    """Return one column's rendered cell for the first row of a plain report-row list.

    Renders the whole table through ``as_html()``, because the escaping lives in the table
    template's ``{{ cell }}``, which ``BoundRow.get_cell()`` never reaches.
    """
    table = ImportReportTable(rows)
    html = table.as_html(RequestFactory().get("/"))
    body_match = re.search(r"<tbody.*?</tbody>", html, re.DOTALL)
    assert body_match, "no table body rendered"
    row_match = re.search(r"<tr.*?</tr>", body_match.group(0), re.DOTALL)
    assert row_match, "no table row rendered"
    cells = re.findall(r"<td.*?</td>", row_match.group(0), re.DOTALL)
    assert len(cells) == len(IMPORT_REPORT_COLUMNS), cells
    return cells[IMPORT_REPORT_COLUMNS.index(column_name)]


class TestOutcomeColumn:
    @pytest.mark.parametrize(
        ("outcome", "variant", "reason"),
        [
            (Outcome.CREATED, "success", None),
            (Outcome.SKIPPED, "warning", None),
            (Outcome.FAILED, "error", "broken"),
        ],
        ids=["created", "skipped", "failed"],
    )
    def test_each_outcome_renders_its_own_mapped_variant(
        self, outcome, variant, reason
    ):
        row = ImportReportRow(
            position=1, outcome=outcome, citation_key=None, reason=reason, item_url=None
        )
        content = import_report_cell([row], "outcome")
        assert f"badge-{variant}" in content

    def test_the_three_outcomes_render_three_distinct_variants(self):
        variants = set()
        for outcome, reason in (
            (Outcome.CREATED, None),
            (Outcome.SKIPPED, None),
            (Outcome.FAILED, "broken"),
        ):
            row = ImportReportRow(
                position=1,
                outcome=outcome,
                citation_key=None,
                reason=reason,
                item_url=None,
            )
            content = import_report_cell([row], "outcome")
            match = re.search(r"badge-(\S+)", content)
            assert match, content
            variants.add(match.group(1))
        assert len(variants) == 3

    def test_the_cell_still_carries_the_outcomes_own_translated_label(self):
        # The badge wraps the label, it does not replace it — a
        # badge showing only its variant, with the word gone, is a
        # regression on the outcome's own distinguishing signal.
        row = ImportReportRow(
            position=1,
            outcome=Outcome.FAILED,
            citation_key=None,
            reason="broken",
            item_url=None,
        )
        content = import_report_cell([row], "outcome")
        assert "Failed" in content


class TestImportReportTable:
    def test_renders_a_list_of_rows_with_no_queryset(self):
        rows = [
            ImportReportRow(
                position=1,
                outcome=Outcome.SKIPPED,
                citation_key=None,
                reason=None,
                item_url=None,
            )
        ]
        table = ImportReportTable(rows)
        assert [row.record for row in table.rows] == rows

    def test_every_column_is_present(self):
        assert set(ImportReportTable.base_columns) == {
            "position",
            "citation_key",
            "outcome",
            "reason",
        }

    def test_the_outcome_cell_renders_the_outcomes_own_translated_label(self):
        # This is what keeps a failed entry distinguishable in
        # place: the word itself, not a class or an icon a reader could miss.
        row = ImportReportRow(
            position=1,
            outcome=Outcome.FAILED,
            citation_key=None,
            reason="broken",
            item_url=None,
        )
        content = import_report_cell([row], "outcome")
        assert "Failed" in content
        assert "failed" not in content  # the stored value, not the label

    def test_a_failure_reason_containing_markup_is_escaped(self):
        row = ImportReportRow(
            position=1,
            outcome=Outcome.FAILED,
            citation_key=None,
            reason="<script>alert(1)</script>",
            item_url=None,
        )
        content = import_report_cell([row], "reason")
        assert "<script>" not in content
        assert "&lt;script&gt;" in content

    def test_a_skipped_rows_reason_renders_in_the_same_column_a_failures_uses(self):
        row = ImportReportRow(
            position=1,
            outcome=Outcome.SKIPPED,
            citation_key=None,
            reason="a @comment block",
            item_url=None,
        )
        content = import_report_cell([row], "reason")
        assert "a @comment block" in content

    def test_a_created_rows_position_links_to_the_item(self):
        row = ImportReportRow(
            position=1,
            outcome=Outcome.CREATED,
            citation_key="Doe2024",
            reason=None,
            item_url="/catalogue/1/",
        )
        content = import_report_cell([row], "position")
        assert 'href="/catalogue/1/"' in content

    def test_a_failed_rows_position_does_not_link(self):
        row = ImportReportRow(
            position=1,
            outcome=Outcome.FAILED,
            citation_key=None,
            reason="broken",
            item_url=None,
        )
        content = import_report_cell([row], "position")
        assert "href=" not in content

    def test_a_created_row_whose_entry_carries_no_citation_key_still_links(self):
        # The link hangs on the position, never on the (absent) key.
        row = ImportReportRow(
            position=1,
            outcome=Outcome.CREATED,
            citation_key=None,
            reason=None,
            item_url="/catalogue/1/",
        )
        content = import_report_cell([row], "position")
        assert 'href="/catalogue/1/"' in content

    def test_the_citation_key_renders_as_plain_text_not_a_link(self):
        row = ImportReportRow(
            position=1,
            outcome=Outcome.CREATED,
            citation_key="Doe2024",
            reason=None,
            item_url="/catalogue/1/",
        )
        content = import_report_cell([row], "citation_key")
        assert "Doe2024" in content
        assert "<a" not in content
