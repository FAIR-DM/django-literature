"""Search and filter definitions for the catalogue, shared by both presentations (FS-010, #96)."""

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

#: The ORM paths a catalogue search matches: the item's identity and title fields,
#: every contributor's name parts whatever the role, and its identifiers.
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

    Not django-filter's ``AllValuesFilter``, which also offers the empty string,
    and ``language`` is blank on most references. The choices are recomputed per
    request, as each request builds a new ``ItemFilterSet``.
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

    A ``Subquery`` rather than a join, as a join multiplies the rows of an item
    carrying more than one ``ItemDate`` and corrupts a paginator's count.

    Args:
        queryset: The ``Item`` queryset to annotate.

    Returns:
        The queryset with an ``issued`` annotation.
    """
    # output_field is explicit because the ``year`` transform that ``issued__year`` needs is
    # registered on DateTimeField, which ItemDate.begin's PartialDateField does not inherit.
    issued_begin = ItemDate.objects.filter(
        item=OuterRef("pk"), date_type=DateType.ISSUED
    ).values("begin")[:1]
    return queryset.annotate(
        issued=Subquery(issued_begin, output_field=DateTimeField())
    )


class ScalarOrListSelectMultiple(forms.SelectMultiple):
    """Accept a bare stored value as well as a list of them, and drop blanks.

    ``SelectMultiple`` reads a list from a ``QueryDict`` but a bare value from a
    plain ``dict``, and ``ItemFilterSet`` is also built directly from a ``dict``.
    A blank entry is dropped because ``?type=`` must mean no filter:
    ``MultipleChoiceField`` would reject a list holding an empty string and
    turn a cleared filter into an empty catalogue.
    """

    def value_from_datadict(self, data, files, name):
        """Widen a bare stored value to a one-item list, and drop blank entries."""
        value = super().value_from_datadict(data, files, name)
        if isinstance(value, str):
            value = [value]
        return [v for v in value if v] if value else value


class TypeChoiceField(filter_fields.MultipleChoiceField):
    """A multiple choice field whose own widget accepts a bare value.

    The widget is the field's default, not passed per filter, so django-mvp's
    toolbar recognises a plain multiple choice and draws its own dropdown.
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
        """Accept a listed year or any other year a date can hold.

        Args:
            value: The submitted year.

        Returns:
            ``True`` if the value is a valid choice.
        """
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

    # A multiple-choice filter so "articles or chapters, from 2019" widens the
    # type while the year narrows it.
    type = TypeFilter(choices=ItemType.choices, label=_("Type"))
    issued_year = YearFilter(method="filter_issued_year", label=_("Year"))
    language = LanguageFilter(label=_("Language"))

    class Meta:
        model = Item
        fields: list[str] = []

    def filter_issued_year(self, queryset, name, value):
        """Match a year-only date and a range beginning in it; no ``issued`` row excludes.

        Narrows on the ``issued`` annotation that ``filter_queryset()`` applies
        first. A reference with no ``issued`` row annotates to ``NULL``, which
        ``__year`` never matches.

        Args:
            queryset: The queryset to narrow.
            name: The filter's name. Unused.
            value: The chosen year.

        Returns:
            The queryset of references issued in that year.
        """
        return queryset.filter(issued__year=value)

    def filter_queryset(self, queryset):
        """Annotate ``issued`` and return each match once."""
        # Annotated unconditionally so ItemTable.order_issued can always sort on it, and
        # distinct() here because the search paths through item_names can multiply rows.
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
        """Leave the queryset alone; ``sort`` only round-trips the table's ordering.

        Args:
            queryset: The queryset, returned unchanged.
            name: The filter's name. Unused.
            value: The chosen column order. Unused.

        Returns:
            The queryset.
        """
        return queryset
