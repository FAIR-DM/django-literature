"""Search and filter definitions for the catalogue (plan.md D-1).

One module, imported by both presentations, so what is searchable and
filterable is declared once (FR-023) rather than restated per view.

``ItemFilterSet`` declares every filter explicitly and pins ``Meta.fields``
to an empty list. django-filter's own default — leaving ``fields`` unset —
generates a filterset over every field of the model, including ``Item``'s
two ``JSONField``s, which django-filter has no filter for and raises on
(plan.md D-6). Never lean on that default anywhere in this module.
"""

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from literature.choices import ItemType
from literature.models import Item

#: The ORM paths a catalogue search matches against (FR-002): the item's own
#: identity and title fields, plus every contributor's name parts regardless
#: of role. Declared once here and imported by both views' ``search_fields``
#: (plan.md D-3) rather than restated in each.
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
    """FR-013: the distinct language values the catalogue holds, as stored.

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
        values = (
            self.model._default_manager.exclude(language="")
            .order_by("language")
            .values_list("language", flat=True)
            .distinct()
        )
        self.extra["choices"] = [(value, value) for value in values]
        return super().field


class ItemFilterSet(django_filters.FilterSet):
    """The catalogue's filters (FR-009 to FR-013): item type, contributor and language.

    The issued year filter is added in T007, alongside the shared ``issued``
    annotation it narrows on.
    """

    type = django_filters.ChoiceFilter(choices=ItemType.choices, label=_("Type"))
    contributor = django_filters.CharFilter(method="filter_contributor", label=_("Contributor"))
    language = LanguageFilter(label=_("Language"))

    class Meta:
        model = Item
        fields: list[str] = []

    def filter_contributor(self, queryset, name, value):
        """FR-011: family, given or literal, in any role — a fragment match, case-insensitive."""
        return queryset.filter(
            Q(item_names__name__family__icontains=value)
            | Q(item_names__name__given__icontains=value)
            | Q(item_names__name__literal__icontains=value)
        )
