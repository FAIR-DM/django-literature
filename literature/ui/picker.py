"""A searchable picker for choosing one reference in a project's own form."""

from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from mvp_forms.widgets import TomSelect, TomSelectMultiple

from literature.choices import NameRole
from literature.models import Item


def item_label(item: Item) -> str:
    """Return the text that names a reference wherever the picker shows it.

    The title (the citation key when there is none), then the issued year in
    brackets, then the first contributor. Whatever a reference lacks is left out.
    Reads ``item_dates`` and ``item_names`` through ``.all()``, so items loaded
    with those prefetched are labelled without a query.

    Args:
        item: The reference to label.

    Returns:
        The label.
    """
    label = item.title or item.citation_key
    year = item.year
    if year is not None:
        label = f"{label} ({year})"
    links = sorted(item.item_names.all(), key=lambda link: link.order)
    authors = [link for link in links if link.role == NameRole.AUTHOR]
    credited = authors or links
    if credited:
        name = credited[0].name.family or credited[0].name.literal
        if name:
            label = f"{label}, {name}"
    return label


class ItemSearchSelect(TomSelect):
    """A Tom Select that draws only the chosen references and searches for the rest.

    The select never lists the catalogue. The script loads matches from the
    search route as the reader types.
    """

    class Media:
        js = ["literature/picker.js"]

    def __init__(self, attrs=None, choices=(), **settings):
        """Default the placeholder to a prompt to search.

        Args:
            attrs: HTML attributes for the select.
            choices: Kept for the field to assign; never drawn.
            **settings: The settings ``TomSelect`` takes.
        """
        settings.setdefault("placeholder", _("Search for a reference…"))
        super().__init__(attrs, choices, **settings)

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Add the address of the search to the select's attributes."""
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs["data-search-url"] = reverse("literature:item-search")
        return attrs

    def optgroups(self, name, value, attrs=None):
        """Return an option for each chosen reference and for nothing else.

        Iterating ``self.choices`` would run the field's whole queryset and
        label every reference, so the chosen ones are read by primary key.
        A value the primary key refuses, or one that no longer exists, is
        left out; the field reports it when the form is validated.
        """
        pks = []
        for raw in value or []:
            try:
                pks.append(Item._meta.pk.to_python(raw))
            except ValidationError:
                continue
        chosen = (
            Item.objects.prefetch_related("item_dates", "item_names__name").in_bulk(pks)
            if pks
            else {}
        )
        options = [
            self.create_option(
                name, str(pk), item_label(chosen[pk]), True, index, attrs=attrs
            )
            for index, pk in enumerate(pk for pk in pks if pk in chosen)
        ]
        return [(None, [option], index) for index, option in enumerate(options)]


class ItemSearchSelectMultiple(ItemSearchSelect, TomSelectMultiple):
    """The search select for several references, with a button to remove each."""

    def __init__(self, attrs=None, choices=(), **settings):
        """Default the remove button on.

        Args:
            attrs: HTML attributes for the select.
            choices: Kept for the field to assign; never drawn.
            **settings: The settings ``TomSelectMultiple`` takes.
        """
        settings.setdefault("remove_button", True)
        super().__init__(attrs, choices, **settings)


class ItemChoiceField(forms.ModelChoiceField):
    """Choose one reference by searching the catalogue.

    On a plain form, declare it as an attribute. On a model form, name it in
    ``Meta.field_classes`` so Django builds it from the model field and keeps
    that field's ``blank`` and ``limit_choices_to``.
    """

    widget = ItemSearchSelect

    def __init__(self, queryset=None, **kwargs):
        """Choose among the whole catalogue unless a queryset is given.

        Args:
            queryset: The references that may be chosen.
            **kwargs: What ``ModelChoiceField`` takes.
        """
        super().__init__(Item.objects.all() if queryset is None else queryset, **kwargs)

    def label_from_instance(self, obj):
        """Label a reference the way the search does."""
        return item_label(obj)


class ItemMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Choose several references by searching the catalogue.

    Declared the same way as ``ItemChoiceField``: an attribute on a plain form,
    or ``Meta.field_classes`` on a model form.
    """

    widget = ItemSearchSelectMultiple

    def __init__(self, queryset=None, **kwargs):
        """Choose among the whole catalogue unless a queryset is given.

        Args:
            queryset: The references that may be chosen.
            **kwargs: What ``ModelMultipleChoiceField`` takes.
        """
        super().__init__(Item.objects.all() if queryset is None else queryset, **kwargs)

    def label_from_instance(self, obj):
        """Label a reference the way the search does."""
        return item_label(obj)
