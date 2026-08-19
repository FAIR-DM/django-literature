"""The catalogue as a table (US-1, FR-001 through FR-012).

New module rather than an addition to ``views.py`` (plan.md D-3): a table
class is neither a view nor a form, and ``views.py`` is already long. Its
mirror test is ``tests/test_ui/test_tables.py``, one module split by
``Test<Column>`` classes per Article XIV.
"""

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _


class ItemTable(tables.Table):
    """The catalogue, one row per reference (FR-001 through FR-012).

    A row's ``contributors`` and ``issued`` cells each read something the
    plain queryset does not carry on its own: ``item.contributors``, a
    ``Prefetch(..., to_attr="contributors")`` restricted to author- and
    editor-role ``ItemName`` rows, and ``item.item_dates``, an ordinary
    prefetch. ``ItemTableView.get_queryset()`` supplies both (plan.md D-2);
    a consumer pairing this table with a plain ``SingleTableView`` of their
    own must supply them too, or pay one query per row for each.
    """

    citation_key = tables.Column(
        verbose_name=_("Citation key"),
        attrs={"td": {"class": "mvp-col-shrink"}, "th": {"class": "mvp-col-shrink"}},
    )
    type = tables.Column(
        verbose_name=_("Type"),
        attrs={"td": {"class": "mvp-col-shrink"}, "th": {"class": "mvp-col-shrink"}},
    )
    title = tables.Column(
        verbose_name=_("Title"),
        attrs={"td": {"class": "mvp-col-wrap mvp-col-max-xl"}},
    )
    container_title = tables.Column(
        verbose_name=_("Container title"),
        attrs={"td": {"class": "mvp-col-wrap mvp-col-max-md"}},
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
