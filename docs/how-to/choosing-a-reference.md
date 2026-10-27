# How to choose a reference in your own form

Add a searchable reference picker to a form in your project, so people find the reference they
mean by typing part of its title, a contributor's name, its citation key or its DOI instead of
scrolling a list of the whole catalogue. The picker chooses from references that already exist.
It does not create one.

`ReferenceField` and `ReferenceMultipleField` are [django-tomselect](https://github.com/OmenApps/django-tomselect)
fields. Their only addition is a default that points at the catalogue's search, so one declaration
works. Everything else about the control is django-tomselect's, and any of its settings can be
passed in.

## Before you start

The picker belongs to the front end, so the project needs `literature.ui` installed and its URLs
mounted, as described in [Installing the front end](../installation.md). The search is one of the
catalogue's routes, so a project that has mounted the catalogue already has it.

django-tomselect arrives with the `ui` extra. Two lines in your settings let it draw a control:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "mvp_forms",
    "django_tomselect",  # after mvp_forms, so django-mvp-forms' template for it wins
    "literature.ui",
]

MIDDLEWARE = [
    # ...
    "django_tomselect.middleware.TomSelectMiddleware",
]
```

## 1. Load the control's files on the page

The page that shows the form loads django-tomselect's script and styles. Render the form's media
once in the page's `<head>` or before the form:

```html
{{ form.media }}
```

On Django 6.1, django-tomselect's own `{% tomselect_media %}` tag writes nothing, so use
`{{ form.media }}` there.

To fit the control into a daisyUI form, also load the stylesheet django-mvp-forms ships for it:

```html
{% load static %}
<link rel="stylesheet" href="{% static 'mvp_forms/tomselect.css' %}">
```

## 2. Declare the field

On a plain form, declare `ReferenceField` as an attribute:

```python
from django import forms

from literature.ui.picker import ReferenceField


class ReviewForm(forms.Form):
    reference = ReferenceField()
```

On a model form, name the field in `Meta.field_classes` instead of declaring it. A field declared
on a model form is used exactly as written, so it would be required whatever the model field's
`blank` says. Naming the class lets Django build the field from the model field, as it does for any
foreign key:

```python
from django import forms

from literature.ui.picker import ReferenceField

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["reference"]
        field_classes = {"reference": ReferenceField}
```

Here `Review.reference` is a `ForeignKey` to `literature.Item`. The field is required unless the
model field has `blank=True`, and a form opened on an existing record shows the reference already
chosen. Submitting a reference that has since been deleted gives the usual `invalid_choice` error.

## 3. Choose several references

To choose several references, use `ReferenceMultipleField` in place of `ReferenceField`:

```python
from django import forms

from literature.ui.picker import ReferenceMultipleField


class BibliographyForm(forms.Form):
    references = ReferenceMultipleField()
```

On a model form, name it in `Meta.field_classes` for a `ManyToManyField`, for the same reason as
above:

```python
from literature.ui.picker import ReferenceMultipleField


class BibliographyForm(forms.ModelForm):
    class Meta:
        model = Bibliography
        fields = ["references"]
        field_classes = {"references": ReferenceMultipleField}
```

The field is required unless the model field has `blank=True`. The form's `cleaned_data` holds a
queryset of the chosen references.

## 4. Change the control's settings

Pass a django-tomselect `TomSelectConfig`, or a dict of its settings, as `config`. It is merged over
the default, so name only what you want to change. The default already holds the search route and
the fields the control reads, so leave `url`, `value_field` and `label_field` alone:

```python
from django_tomselect.app_settings import PluginRemoveButton, TomSelectConfig

from literature.ui.picker import ReferenceMultipleField


class BibliographyForm(forms.Form):
    references = ReferenceMultipleField(
        config=TomSelectConfig(
            placeholder="Find a source",
            max_items=5,
            plugin_remove_button=PluginRemoveButton(title="Drop this source"),
        )
    )
```

django-tomselect's documentation lists every setting.

## 5. Restrict which references are offered

Use django-tomselect's `filter_by` and `exclude_by`. A constant condition is written with `Const`,
which takes the value and the Django lookup:

```python
from django_tomselect.app_settings import Const, TomSelectConfig

from literature.ui.picker import ReferenceField


class ReviewForm(forms.Form):
    reference = ReferenceField(
        config=TomSelectConfig(
            filter_by=Const("book", "type"),
            exclude_by=Const("fr", "language"),
        )
    )
```

The search offers only books not in French, and the form refuses any other reference with
`invalid_choice` when it is submitted. django-tomselect itself validates a submission against the
search view's whole queryset, so the fields apply a constant condition again themselves. A list
lookup takes a list: `Const(["book", "article"], "type__in")`.

A condition that takes its value from another field of the same form (`FilterSpec` with
`source_type="field"`, or the legacy `("field", "lookup")` pair) narrows the search as the person
changes that field. The form does not check it on submit; that is django-tomselect's own behaviour.

A `queryset=` passed to the field, and a model field's `limit_choices_to`, are not used: the search
view decides what is offered, and `filter_by` and `exclude_by` narrow it.

## What the search matches

The picker searches exactly as the catalogue's own search box does. A reference is offered when
any word typed appears in any one of:

- its titles, including the short, original and container titles
- its citation key
- a contributor's family or given name, or the literal name of an organisation
- any of its identifiers, such as a DOI or an ISBN. A DOI is found with or without a
  `https://doi.org/` address or a `doi:` label in front, in any letter case.

Opening the picker shows the first references in the catalogue, by title, before anything is
typed. Typing narrows them from the first character.

Case does not matter. Typing `%`, `_` or a quotation mark matches those characters and nothing
else. A reference that matches in several ways is offered once. A title or citation key that
starts with the whole text comes first, and at most 20 references are offered at a time, with more loaded
as the list is scrolled. Each is shown as its title (its citation key when it has no title), its
year and its first contributor, preferring an author when it has one. Text of more than 200
characters is cut to 200, and text containing a NUL character is refused.

## Who may search

The search follows the catalogue list's read access, which is open to everyone. A reference the
search offers is already visible on the list, so it reveals nothing the list does not. To close it,
close the catalogue's read routes together by guarding the include where you mount them. The
search is closed along with the list and the reference pages, and the package has no separate
setting for it.
