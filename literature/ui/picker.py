"""Searchable fields for choosing references in a project's own form."""

from django.core.exceptions import ValidationError
from django_tomselect.app_settings import TomSelectConfig, merge_configs
from django_tomselect.forms import (
    TomSelectModelChoiceField,
    TomSelectModelMultipleChoiceField,
)

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


class _ReferencePicker:
    """What the two reference fields share: a default config and a restriction check.

    The default config points django-tomselect at the package's search route.
    A config the developer passes is merged over it, so any django-tomselect
    setting can be added. django-tomselect validates a submission against the
    search view's whole queryset, so a chosen reference is also checked against
    the config's constant ``filter_by`` and ``exclude_by`` conditions. A
    condition that takes its value from another form field is left to
    django-tomselect.
    """

    default_config = TomSelectConfig(
        url="literature:item-search", value_field="id", label_field="label"
    )

    def __init__(self, *args, config=None, **kwargs):
        """Merge the developer's config over the default.

        Args:
            *args: What the django-tomselect field takes.
            config: A ``TomSelectConfig`` or a dict of its settings.
            **kwargs: What the django-tomselect field takes.
        """
        if config is not None and not isinstance(config, TomSelectConfig):
            config = TomSelectConfig(**config)
        super().__init__(
            *args, config=merge_configs(self.default_config, config), **kwargs
        )

    def clean(self, value):
        """Refuse a chosen reference outside the config's constant conditions."""
        cleaned = super().clean(value)
        chosen = [cleaned] if isinstance(cleaned, Item) else cleaned
        if chosen and not self._within_restriction([item.pk for item in chosen]):
            raise ValidationError(
                self.error_messages["invalid_choice"],
                code="invalid_choice",
                params={"value": value},
            )
        return cleaned

    def _within_restriction(self, pks):
        """Return whether every pk meets the constant conditions."""
        queryset = Item.objects.filter(pk__in=pks)
        for spec in self.config.get_normalized_filters():
            if spec.source_type == "const":
                queryset = queryset.filter(**{spec.lookup: self._value_of(spec)})
        for spec in self.config.get_normalized_excludes():
            if spec.source_type == "const":
                queryset = queryset.exclude(**{spec.lookup: self._value_of(spec)})
        return queryset.count() == len(set(pks))

    @staticmethod
    def _value_of(spec):
        """Return a constant condition's value, split when its lookup takes a list."""
        if spec.lookup.rsplit("__", 1)[-1] in ("in", "range"):
            return spec.source.split(",")
        return spec.source


class ReferenceField(_ReferencePicker, TomSelectModelChoiceField):
    """Choose one reference by searching the catalogue.

    On a plain form, declare it as an attribute. On a model form, name it in
    ``Meta.field_classes`` so Django builds it from the model field.
    """


class ReferenceMultipleField(_ReferencePicker, TomSelectModelMultipleChoiceField):
    """Choose several references by searching the catalogue.

    Declared the same way as ``ReferenceField``.
    """
