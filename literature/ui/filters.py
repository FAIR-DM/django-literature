"""Search and filter definitions for the catalogue (FS-010, #96).

One module, imported by both presentations, so what is searchable and
filterable is declared once rather than restated per view.

``ItemFilterSet`` declares every filter explicitly and pins ``Meta.fields``
to an empty list. django-filter's own default — leaving ``fields`` unset —
generates a filterset over every field of the model, including ``Item``'s
two ``JSONField``s, which django-filter has no filter for and raises on.
Never lean on that default anywhere in this module.
"""

import django_filters
from django import forms
from django.db.models import DateTimeField, OuterRef, Q, Subquery
from django.utils.translation import gettext_lazy as _

from literature.choices import DateType, ItemType
from literature.models import Item, ItemDate

#: The ORM paths a catalogue search matches against: the item's own
#: identity and title fields, plus every contributor's name parts regardless
#: of role. Declared once here and imported by both views' ``search_fields``
#: rather than restated in each.
SEARCH_FIELDS = [
    "citation_key",
    "title",
    "title_short",
    "original_title",
    "container_title",
    "item_names__name__family",
    "item_names__name__given",
    "item_names__name__literal",
]


class LanguageFilter(django_filters.ChoiceFilter):
    """The distinct language values the catalogue holds, as stored.

    Not django-filter's own ``AllValuesFilter`` (the same idiom this
    subclasses): that offers every stored value including the empty string,
    and ``language`` is free text and blank on most references today.
    ``self.model`` is assigned by ``BaseFilterSet.__init__`` on every filter
    instance, so this is safe to read without the class declaring it itself,
    and it is recomputed on every request — a new ``ItemFilterSet`` instance
    each time — rather than once at import time.
    """

    @property
    def field(self):
        """The choice field, its choices refreshed from the stored language values."""
        values = (
            self.model._default_manager.exclude(language="")
            .order_by("language")
            .values_list("language", flat=True)
            .distinct()
        )
        self.extra["choices"] = [(value, value) for value in values]
        return super().field


def annotate_issued(queryset):
    """Annotate ``issued`` from the ``issued`` date slot's ``begin``.

    The same ``Subquery`` FS-009 wrote inline in ``ItemTableView.get_queryset()``
    for the table's own sort column, moved here so it is declared once. A
    ``Subquery`` rather than a join: a join multiplies a row for an item
    carrying more than one ``ItemDate``, corrupting a paginator's count.

    ``output_field=DateTimeField()`` is stated explicitly rather than left to
    infer ``ItemDate.begin``'s own ``PartialDateField``: Django registers the
    ``year`` transform ``filter_issued_year`` below needs on ``DateField``/
    ``DateTimeField`` specifically, and a third-party field that only
    overrides ``get_internal_type()`` to report ``"DateTimeField"`` (for the
    database column) does not inherit it — confirmed directly,
    ``issued__year`` otherwise raises ``FieldError: Unsupported lookup
    'year'``. Ordering (``ItemTable.order_issued``) is unaffected either way,
    since it sorts on the raw column value, not through a lookup.
    """
    issued_begin = ItemDate.objects.filter(
        item=OuterRef("pk"), date_type=DateType.ISSUED
    ).values("begin")[:1]
    return queryset.annotate(
        issued=Subquery(issued_begin, output_field=DateTimeField())
    )


class ScalarOrListSelectMultiple(forms.SelectMultiple):
    """Accept a bare stored value as well as a list of them, and drop blanks.

    ``SelectMultiple.value_from_datadict`` reads ``data.getlist(name)`` for
    a real ``QueryDict`` — an HTTP GET's own multi-value form, where even
    one chosen option arrives as a one-item list — but falls back to plain
    ``data.get(name)`` for an ordinary ``dict``, returning a bare value.
    ``ItemFilterSet`` is also constructed directly with a plain ``dict`` and
    a bare stored value (``tests/test_ui/test_filters.py``), the same call
    the single-value ``ChoiceFilter`` this replaces took; wrapping a bare
    value in a list here keeps that call narrowing to one type exactly as
    it always did, rather than requiring every direct construction to know
    this filter now also widens.

    A blank entry is dropped rather than passed through: the single-value
    ``ChoiceFilter`` this replaces treated ``?type=`` as no value at all
    (``Filter.filter()``'s own ``EMPTY_VALUES`` no-op), where
    ``MultipleChoiceField.validate()`` has no such allowance and would
    reject a list holding an empty string as not a valid choice — turning a
    cleared filter into an invalid one and, under ``strict``, an empty
    catalogue instead of the unfiltered one clearing it must restore. An
    actually-invalid value is a separate case this does not govern.
    """

    def value_from_datadict(self, data, files, name):
        """Widen a bare stored value to a one-item list, and drop blank entries."""
        value = super().value_from_datadict(data, files, name)
        if isinstance(value, str):
            value = [value]
        return [v for v in value if v] if value else value


def get_active_filters(filterset):
    """Filters actually in force, the hidden ``sort`` field excluded.

    Mirrors ``MVPFilteredListView.get_active_filters()``
    (``mvp/integrations/django_filters/views.py``) — dropping every empty,
    null or default-like value from ``filterset.form.cleaned_data`` — plus
    the one field neither presentation ever counts: ``sort`` is a hidden
    field on this form only to round-trip django-tables2's own ordering
    (``ItemFilterSet.sort`` below), not one of the catalogue's four
    filters. One definition, called from both ``ItemListView`` and
    ``ItemTableView``, so the exclusion is not restated twice.
    """
    if not hasattr(filterset.form, "cleaned_data"):
        return {}
    return {
        name: value
        for name, value in filterset.form.cleaned_data.items()
        if name != "sort" and value not in (None, "", [], (), False)
    }


class ItemFilterSet(django_filters.FilterSet):
    """The catalogue's filters (FS-010, #96): item type, contributor, language and issued year."""

    # MultipleChoiceFilter, not ChoiceFilter: this filter's own worked
    # example — "articles or chapters, from 2019" — widens type to either
    # value while year narrows what that widened set returns.
    # MultipleChoiceFilter.filter() ORs the chosen values by default
    # (``conjoined=False``), which is exactly that widening.
    type = django_filters.MultipleChoiceFilter(
        choices=ItemType.choices, label=_("Type"), widget=ScalarOrListSelectMultiple
    )
    contributor = django_filters.CharFilter(
        method="filter_contributor", label=_("Contributor")
    )
    language = LanguageFilter(label=_("Language"))
    issued_year = django_filters.NumberFilter(
        method="filter_issued_year", label=_("Year")
    )

    # Not one of the four catalogue filters: carries the table's own sort
    # (django-tables2's `order_by_field`, "sort") across a change of
    # filter. The filter form is our own GET form, rendered by the
    # component from `filter.form` (mvp's own crispy-forms render, which
    # emits a hidden field's <input> with no template change of ours
    # needed), so a hidden field here round-trips through it where an
    # upstream pagination-style link previously did not. `filter_sort()`
    # is a deliberate no-op: ordering is django-tables2's own concern
    # (`ItemTable.Meta.order_by`), not the filterset's — this field exists
    # only to be present on the form and carried forward when it is
    # resubmitted. `ItemTableView.get_context_data()` excludes this key
    # from what it reports as an applied filter: a hidden field is still a
    # form field, and django-mvp counts every non-empty one.
    sort = django_filters.CharFilter(
        method="filter_sort", widget=forms.HiddenInput(), required=False
    )

    class Meta:
        model = Item
        fields: list[str] = []

    def filter_sort(self, queryset, name, value):
        """No-op: ``sort`` only round-trips django-tables2's own ordering through this form."""
        return queryset

    def filter_contributor(self, queryset, name, value):
        """Match ``value`` against a contributor's family, given or literal name, in any role.

        A fragment match, case-insensitive.
        """
        return queryset.filter(
            Q(item_names__name__family__icontains=value)
            | Q(item_names__name__given__icontains=value)
            | Q(item_names__name__literal__icontains=value)
        )

    def filter_issued_year(self, queryset, name, value):
        """Match a year-only date and a range beginning in it; no ``issued`` row excludes.

        Narrows on the ``issued`` annotation ``filter_queryset()`` always
        applies first, so this runs whether ``annotate_issued()`` was called
        by a caller already or not. A reference with no ``issued`` row
        annotates to ``NULL``, and ``__year`` against ``NULL`` never matches
        — no separate exclusion is written for it.
        """
        return queryset.filter(issued__year=value)

    def filter_queryset(self, queryset):
        """Annotate ``issued`` and return each match once, however many of its rows matched.

        ``annotate_issued()`` runs first and unconditionally — not only when
        the year filter has a value — so the ``issued`` column is present
        for a consumer that sorts on it (``ItemTable.order_issued``)
        regardless of whether a year was requested. Three of the four
        filters and three of the eight search paths traverse ``item_names``,
        so a join can multiply a reference's rows; ``.distinct()`` lives
        here, once, rather than in each view — the search path needs no
        equivalent of its own, since the mixin's own query already ends in
        ``.distinct()``.
        """
        queryset = annotate_issued(queryset)
        return super().filter_queryset(queryset).distinct()
