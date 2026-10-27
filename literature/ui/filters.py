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
from django.db.models import DateTimeField, OuterRef, Subquery
from django.db.models.functions import ExtractYear
from django.utils.translation import gettext_lazy as _
from django_filters import fields as filter_fields
from mvp.filters import SearchFilter

from literature.choices import DateType, ItemType
from literature.importers.normalizers import IdentifierNormalizer
from literature.models import Item, ItemDate

#: The ORM paths a catalogue search matches against: the item's own
#: identity and title fields, every contributor's name parts regardless of
#: role, and its identifiers. Declared once here and read by
#: ``ItemFilterSet.q``, which the catalogue and the reference picker share.
SEARCH_FIELDS = [
    "citation_key",
    "title",
    "title_short",
    "original_title",
    "container_title",
    "item_names__name__family",
    "item_names__name__given",
    "item_names__name__literal",
    "item_identifiers__value",
]


class CatalogueSearchFilter(SearchFilter):
    """django-mvp's search, with each word read as a DOI would be stored.

    A DOI pasted with its ``https://doi.org/`` address or a ``doi:`` label in
    front finds the reference that stores the bare DOI. A word that is only
    such a prefix searches nothing.
    """

    def filter(self, qs, value):
        """Strip DOI prefixes from each word, then search as django-mvp does."""
        words = (
            IdentifierNormalizer.normalize_doi(word) for word in (value or "").split()
        )
        return super().filter(qs, " ".join(word for word in words if word))


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


class TypeChoiceField(filter_fields.MultipleChoiceField):
    """A multiple choice field whose own widget accepts a bare value.

    Declared as the field's default widget, not passed per filter, so
    django-mvp's toolbar recognises the filter as a plain multiple choice and
    draws its own dropdown for it.
    """

    widget = ScalarOrListSelectMultiple


class TypeFilter(django_filters.MultipleChoiceFilter):
    """Item type, any of several, through ``TypeChoiceField``."""

    field_class = TypeChoiceField


class YearChoiceField(filter_fields.ChoiceField):
    """A choice of the years held that still accepts any other year.

    A year no reference was issued in, from an old bookmark, narrows the
    catalogue to nothing rather than being dropped as an invalid choice and
    showing every reference (FS-010). A value that is not a year, or a year
    outside the 1 to 9999 a Python date can hold, is still invalid, so the
    filter ignores it rather than failing on the date lookup.
    """

    def valid_value(self, value):
        """Accept a listed year or any other year a date can hold."""
        value = str(value)
        return (value.isdigit() and 1 <= int(value) <= 9999) or super().valid_value(
            value
        )


class YearFilter(django_filters.ChoiceFilter):
    """The issued years the catalogue holds, newest first, through ``YearChoiceField``."""

    field_class = YearChoiceField

    @property
    def field(self):
        """The choice field, its choices refreshed from the stored issued years."""
        years = (
            annotate_issued(self.model._default_manager.all())
            .exclude(issued=None)
            .annotate(year=ExtractYear("issued"))
            .order_by("-year")
            .values_list("year", flat=True)
            .distinct()
        )
        self.extra["choices"] = [(str(year), str(year)) for year in years]
        return super().field


class ItemFilterSet(django_filters.FilterSet):
    """The catalogue's search and filters (FS-010, #96): item type, issued year and language.

    Search covers contributor names, so there is no separate contributor filter.
    """

    q = CatalogueSearchFilter(fields=SEARCH_FIELDS)

    # MultipleChoiceFilter, not ChoiceFilter: this filter's own worked
    # example — "articles or chapters, from 2019" — widens type to either
    # value while year narrows what that widened set returns.
    # MultipleChoiceFilter.filter() ORs the chosen values by default
    # (``conjoined=False``), which is exactly that widening.
    type = TypeFilter(choices=ItemType.choices, label=_("Type"))
    issued_year = YearFilter(method="filter_issued_year", label=_("Year"))
    language = LanguageFilter(label=_("Language"))

    class Meta:
        model = Item
        fields: list[str] = []

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
        regardless of whether a year was requested. Three of the eight
        search paths traverse ``item_names``, so a join can multiply a
        reference's rows; ``.distinct()`` lives here, once, rather than in
        each view.
        """
        queryset = annotate_issued(queryset)
        return super().filter_queryset(queryset).distinct()


class ItemTableFilterSet(ItemFilterSet):
    """The catalogue's filters plus the table's own ordering, carried by the form.

    The table sorts through django-tables2's ``sort`` query parameter. The
    filter form is a plain GET form, so a hidden field here keeps the chosen
    column order when the form is submitted again.
    """

    sort = django_filters.CharFilter(
        method="filter_sort",
        label=_("Sort"),
        widget=forms.HiddenInput(),
        required=False,
    )

    def filter_sort(self, queryset, name, value):
        """No-op: ``sort`` only round-trips django-tables2's own ordering through this form."""
        return queryset
