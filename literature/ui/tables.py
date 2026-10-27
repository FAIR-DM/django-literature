"""The catalogue as a table (FS-009, #87)."""

import django_tables2 as tables
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from literature.choices import DateType, NameRole
from literature.importers.results import Outcome


class ContributorsColumn(tables.TemplateColumn):
    """The credited-names cell.

    Selects the values only: the author-role names the view prefetched onto the
    record as ``contributors`` (editor-role names if there are no authors), the
    first three plus a count of the rest. The template builds the markup, as a
    name is free text and nothing here is passed through ``mark_safe``. A record
    with no prefetch degrades to the empty-value marker rather than querying
    once per row.
    """

    def get_context_data(self, record, **kwargs):
        """Add the credited names and the hidden-remainder count."""
        context = super().get_context_data(record=record, **kwargs)
        item_names = getattr(record, "contributors", [])
        authors = [
            item_name.name
            for item_name in item_names
            if item_name.role == NameRole.AUTHOR
        ]
        credited = authors or [
            item_name.name
            for item_name in item_names
            if item_name.role == NameRole.EDITOR
        ]
        context["names"] = credited[:3]
        context["hidden_count"] = max(len(credited) - 3, 0)
        return context


class IssuedColumn(tables.TemplateColumn):
    """The issued-date cell.

    Picks the ``issued`` slot off the record's prefetched ``item_dates`` and hands
    it to ``date_value.html``, so the precision-and-range rule lives in that one
    partial.
    """

    def get_context_data(self, record, **kwargs):
        """Add the record's own ``issued`` date, if it has one."""
        context = super().get_context_data(record=record, **kwargs)
        context["item_date"] = next(
            (
                item_date
                for item_date in record.item_dates.all()
                if item_date.date_type == DateType.ISSUED
            ),
            None,
        )
        return context


class ItemTable(tables.Table):
    """The catalogue, one row per reference.

    The ``contributors`` and ``issued`` cells read two prefetches that
    ``ItemTableView.get_queryset()`` supplies: ``contributors`` (author- and
    editor-role ``ItemName`` rows) and ``item_dates``. A view of a consumer's own
    must supply them too, or pay one query per row for each.
    """

    citation_key = tables.Column(
        verbose_name=_("Citation key"),
        # Every sortable column ends on ``pk``: without a tiebreak, tied rows have no
        # total order and a reference can appear on two pages or none (PostgreSQL).
        order_by=("citation_key", "pk"),
        attrs={"td": {"class": "mvp-col-shrink"}, "th": {"class": "mvp-col-shrink"}},
    )
    type = tables.Column(
        verbose_name=_("Type"),
        order_by=("type", "pk"),
        attrs={"td": {"class": "mvp-col-shrink"}, "th": {"class": "mvp-col-shrink"}},
        # No render_type: django-tables2 already shows get_type_display().
    )
    title = tables.Column(
        verbose_name=_("Title"),
        # Without this, an empty title never reaches render_title and its fallback chain.
        empty_values=(),
        order_by=("title", "pk"),
        linkify=True,
        attrs={
            "a": {"class": "link link-primary"},
            "td": {"class": "mvp-col-wrap mvp-col-max-xl"},
        },
    )
    container_title = tables.Column(
        verbose_name=_("Container title"),
        order_by=("container_title", "pk"),
        attrs={"td": {"class": "mvp-col-wrap mvp-col-max-md"}},
    )
    contributors = ContributorsColumn(
        verbose_name=_("Authors"),
        template_name="literature/ui/table_contributors.html",
        empty_values=(),
        # A through-model across two roles has no single value to order on.
        orderable=False,
        # django-mvp centres a non-orderable column it cannot resolve to a field; this is
        # free text, so it is left-aligned like the other text columns.
        attrs={"td": {"class": "text-start mvp-col-wrap mvp-col-max-md"}},
    )
    issued = IssuedColumn(
        verbose_name=_("Issued"),
        template_name="literature/ui/table_issued.html",
        empty_values=(),
        # Names the "issued" annotation that ItemTableView.get_queryset() supplies.
        order_by="issued",
        attrs={"td": {"class": "mvp-col-shrink"}, "th": {"class": "mvp-col-shrink"}},
    )

    class Meta:
        # No model or fields: with a model, django-tables2 adds a column for every field.
        template_name = "django_tables2/bootstrap5-mvp.html"
        # A flag only: django-mvp's template shows the view's own empty-state text instead.
        empty_text = _("Nothing to show.")
        default = _("—")
        # No order_by: newest-first comes from Item.Meta.ordering.

    def render_title(self, record):
        """Return the first value the reference carries down its title chain.

        The chain ends at the citation key, so a title-less reference shows its key
        rather than an empty-value marker as link text.

        Args:
            record: The ``Item`` being rendered.

        Returns:
            The text for the title cell.
        """
        return (
            record.title
            or record.title_short
            or record.original_title
            or record.volume_title
            or record.citation_key
        )

    def order_issued(self, queryset, is_descending):
        """Sort by the ``issued`` annotation, undated references last either way.

        SQLite and PostgreSQL place NULLs differently, so ``nulls_last=True`` is
        stated in both directions.

        Args:
            queryset: The queryset to order.
            is_descending: Whether the sort is descending.

        Returns:
            The ordered queryset and ``True``, which tells django-tables2 the
            queryset is already ordered.
        """
        issued = F("issued")
        ordering = (
            issued.desc(nulls_last=True)
            if is_descending
            else issued.asc(nulls_last=True)
        )
        # ``pk`` last, as the column ordering above.
        return queryset.order_by(ordering, "pk"), True


class OutcomeColumn(tables.TemplateColumn):
    """The outcome cell (FS-011, #103).

    Renders django-mvp's ``<c-badge>`` around the outcome's translated label, so a
    failed entry is told apart by the word and not only by colour. Skipped is a
    warning rather than neutral because a skipped entry may carry a reason
    (docs/adr/0027-a-skipped-entry-may-carry-a-reason.md). The template, not
    ``mark_safe``, escapes the label.
    """

    VARIANTS = {
        Outcome.CREATED: "success",
        Outcome.SKIPPED: "warning",
        Outcome.FAILED: "error",
    }

    def get_context_data(self, record, **kwargs):
        """Add the outcome's badge variant and its translated label."""
        context = super().get_context_data(record=record, **kwargs)
        context["variant"] = self.VARIANTS[record.outcome]
        context["label"] = record.outcome.label
        return context


class ImportReportTable(tables.Table):
    """The import report, one row per entry the format found (FS-011, #103).

    Built over a plain list of :class:`~literature.ui.importing.ImportReportRow`,
    as the report has no model behind it. The position column carries the link
    because a created row's citation key may be absent and its position never is.
    """

    position = tables.Column(
        verbose_name=_("Position"),
        linkify=lambda record: record.item_url,
        attrs={"td": {"class": "mvp-col-shrink"}, "th": {"class": "mvp-col-shrink"}},
    )
    citation_key = tables.Column(verbose_name=_("Citation key"))
    outcome = OutcomeColumn(
        verbose_name=_("Outcome"),
        template_name="literature/ui/table_outcome.html",
        empty_values=(),
    )
    reason = tables.Column(verbose_name=_("Reason"))

    class Meta:
        template_name = "django_tables2/bootstrap5-mvp.html"
        empty_text = _("Nothing to show.")
        default = _("—")
        # Fixed source order, so no header advertises a sort control.
        orderable = False
