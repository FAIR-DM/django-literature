"""The catalogue as a table (US-1, FR-001 through FR-012).

New module rather than an addition to ``views.py`` (plan.md D-3): a table
class is neither a view nor a form, and ``views.py`` is already long. Its
mirror test is ``tests/test_ui/test_tables.py``, one module split by
``Test<Column>`` classes per Article XIV.
"""

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from django_tables2.utils import A

from literature.choices import DateType, NameRole


class ContributorsColumn(tables.TemplateColumn):
    """The credited-names cell (FR-006 through FR-008).

    Selects the values only — reading the ``contributors`` attribute
    ``ItemTableView.get_queryset()`` prefetches onto the record (a
    ``Prefetch(..., to_attr="contributors")``), author-role names if the
    item has any, else editor-role names, first three plus the count of the
    rest — and leaves building the markup to the template (plan.md D-6,
    Article V): a contributor's name is free text entered through this
    package's own open write pages, and nothing here is passed through
    ``mark_safe``. ``getattr(record, "contributors", [])`` reads the
    prefetch defensively, so a record drawn through a plain
    ``SingleTableView`` with no prefetch degrades to the empty-value marker
    rather than raising (research R9) — and never touches the manager, which
    would cost one query per row.
    """

    def get_context_data(self, record, **kwargs):
        context = super().get_context_data(record=record, **kwargs)
        item_names = getattr(record, "contributors", [])
        authors = [item_name.name for item_name in item_names if item_name.role == NameRole.AUTHOR]
        credited = authors or [item_name.name for item_name in item_names if item_name.role == NameRole.EDITOR]
        context["names"] = credited[:3]
        context["hidden_count"] = max(len(credited) - 3, 0)
        return context


class IssuedColumn(tables.TemplateColumn):
    """The issued-date cell (FR-009).

    Picks the ``issued`` date slot off the record's prefetched
    ``item_dates`` and hands it to ``date_value.html`` under the name it
    expects, so the precision-and-range rule stays in that one shared
    partial rather than forking into a second Python implementation
    (research R8, plan.md D-7). ``.all()`` on a prefetched relation reads
    the cache rather than issuing a query, exactly as ``item_list_item.html``
    already relies on for the same relation.
    """

    def get_context_data(self, record, **kwargs):
        context = super().get_context_data(record=record, **kwargs)
        context["item_date"] = next(
            (item_date for item_date in record.item_dates.all() if item_date.date_type == DateType.ISSUED),
            None,
        )
        return context


class ActionsColumn(tables.TemplateColumn):
    """The row's edit control (FR-019, FR-020).

    ``ItemTableView.get_table_kwargs()`` hands the table
    ``show_update_action`` — the same ``CRUDDirectoryMixin`` flag
    ``ItemDetailView``'s own edit action reads through
    ``self.show_action("update")`` — as ``table.show_update_action``. This
    column selects that value into the cell's context; the outer page
    context is not relied on, since a ``TemplateColumn``'s cell renders
    through Cotton's own isolated context and cannot be assumed to inherit
    it (see ``ItemTable.__init__``).
    """

    def get_context_data(self, table, **kwargs):
        context = super().get_context_data(table=table, **kwargs)
        context["show_update_action"] = table.show_update_action
        return context


class ItemTable(tables.Table):
    """The catalogue, one row per reference (FR-001 through FR-012).

    A row's ``contributors`` and ``issued`` cells each read something the
    plain queryset does not carry on its own: ``item.contributors``, a
    ``Prefetch(..., to_attr="contributors")`` restricted to author- and
    editor-role ``ItemName`` rows, and ``item.item_dates``, an ordinary
    prefetch. ``ItemTableView.get_queryset()`` supplies both (plan.md D-2);
    a consumer pairing this table with a plain ``SingleTableView`` of their
    own must supply them too, or pay one query per row for each.

    ``show_update_action`` (FR-019, FR-020) gates the actions cell's edit
    control. It defaults to ``True`` — a bare ``ItemTable`` is open, matching
    this feature's rule that it introduces no access control of its own —
    and ``ItemTableView.get_table_kwargs()`` overrides it with
    ``self.show_action("update")``, the same ``CRUDDirectoryMixin`` flag
    ``ItemDetailView``'s own edit action already reads.
    """

    def __init__(self, *args, show_update_action=True, **kwargs):
        self.show_update_action = show_update_action
        super().__init__(*args, **kwargs)

    citation_key = tables.Column(
        verbose_name=_("Citation key"),
        attrs={"td": {"class": "mvp-col-shrink"}, "th": {"class": "mvp-col-shrink"}},
    )
    type = tables.Column(
        verbose_name=_("Type"),
        order_by="type",
        attrs={"td": {"class": "mvp-col-shrink"}, "th": {"class": "mvp-col-shrink"}},
        # No renderer, deliberately: django-tables2 resolves a choice field
        # through get_FOO_display() before any renderer runs (rows.py), so
        # the translated label (FR-005) arrives on its own while order_by
        # above keeps ordering on the stored value (FR-017). A render_type
        # here would only restate what the library already does — do not
        # add one back.
    )
    title = tables.Column(
        verbose_name=_("Title"),
        # Mandatory: without it, an item whose title resolves to "" never
        # reaches render_title, defeating the fallback chain in exactly the
        # case it exists for (research R3).
        empty_values=(),
        order_by="title",
        # Item has no get_absolute_url(), so linkify=True cannot be used
        # (research R2) — the route lives in the table class, inside
        # literature/ui/.
        linkify=("literature:item-detail", {"pk": A("pk")}),
        attrs={
            "a": {"class": "link link-hover"},
            "td": {"class": "mvp-col-wrap mvp-col-max-xl"},
        },
    )
    container_title = tables.Column(
        verbose_name=_("Container title"),
        attrs={"td": {"class": "mvp-col-wrap mvp-col-max-md"}},
    )
    contributors = ContributorsColumn(
        verbose_name=_("Authors"),
        template_name="literature/ui/table_contributors.html",
        empty_values=(),
        # An through-model across two roles has no single value to order on
        # (FR-015).
        orderable=False,
    )
    issued = IssuedColumn(
        verbose_name=_("Issued"),
        template_name="literature/ui/table_issued.html",
        empty_values=(),
        # The annotation and order_issued that make the sort resolvable do
        # not land until US-3 (T017/T018) — a header advertising a sort
        # before then raises FieldError on the package's default page.
        orderable=False,
        attrs={"td": {"class": "mvp-col-shrink"}, "th": {"class": "mvp-col-shrink"}},
    )
    actions = ActionsColumn(
        verbose_name="",
        template_name="literature/ui/table_actions.html",
        empty_values=(),
        # A control, not data — no single value to order on (FR-015). Also
        # what earns the column its centred alignment (research R6).
        orderable=False,
    )

    class Meta:
        # No model: with one set and no `fields`, django-tables2 generates a
        # column for every field on the model in addition to the ones
        # declared here — exactly the silent-column problem `fields` being
        # unset is meant to avoid. Column alignment still infers correctly
        # (mvp/templatetags/mvp.py's `column_alignment_class` reads
        # `table.data.model`, off the queryset itself, not `Meta.model`).
        template_name = "django_tables2/bootstrap5-mvp.html"
        # A flag, not displayed text — the mvp template renders its empty
        # state inside `{% if table.empty_text %}` and shows the view's own
        # empty_state_heading/message instead (research R5).
        empty_text = _("Nothing to show.")
        # FR-010's empty-value marker, translatable — replaces the
        # library's own plain "—" default (Article VIII).
        default = _("—")
        # No order_by: an alias naming a column that does not exist (e.g.
        # "created") is silently dropped by django-tables2, and FR-002
        # forbids a "created" column existing to name. Newest-first comes
        # from Item.Meta.ordering, exactly as ItemListView already relies
        # on (plan.md D-3).
        # No fields: every column is declared explicitly, so a field added
        # to Item later never silently becomes a column.

    def render_title(self, record):
        """The first value the reference carries down its title chain (FR-003).

        Ends at the citation key, which is also its own column — a link
        whose text is the empty-value marker cannot be read or clicked with
        confidence, so a title-less reference duplicates its key instead.
        """
        return record.title or record.title_short or record.original_title or record.volume_title or record.citation_key
