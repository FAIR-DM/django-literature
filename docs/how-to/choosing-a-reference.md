# How to choose a reference in your own form

Add a searchable reference picker to a form in your project, so people find the reference they
mean by typing part of its title, a contributor's name, its citation key or its DOI instead of
scrolling a list of the whole catalogue. The picker chooses from references that already exist.
It does not create one.

## Before you start

The picker belongs to the front end, so the project needs `literature.ui` installed and its URLs
mounted, as described in [Installing the front end](../installation.md). The search is one of the
catalogue's routes, so a project that has mounted the catalogue already has it.

## 1. Load Tom Select on the page

The picker draws a [Tom Select](https://tom-select.js.org/) control. The page that shows the form
loads Tom Select itself, and a page without it leaves the control as an ordinary select. Add these
tags to the page's `<head>`, copied from the package's own form page, `item_form.html`:

```html
{% load static %}
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/tom-select@2.5.2/dist/css/tom-select.default.min.css"
      integrity="sha384-ysUSQKRs8NxL3MLtPxj9HZ7KmGXzQJwr8rfFRR8iT5A26QF3slDzsChy8nZ7Q1W2"
      crossorigin="anonymous">
<link rel="stylesheet" href="{% static 'mvp_forms/tomselect.css' %}">
<script src="https://cdn.jsdelivr.net/npm/tom-select@2.5.2/dist/js/tom-select.complete.min.js"
        integrity="sha384-zpRmcxaWZMsftDGxJwwTBxLTwPZrI4VJXe2bYlo01xaeBAdQjHP/nPlVH83BCW0U"
        crossorigin="anonymous"></script>
```

Render the form's media once on the page, after the tags above, so the scripts that start the
control and give it its search load too:

```html
{{ form.media }}
```

## 2. Declare the field

On a plain form, declare `ItemChoiceField` as an attribute:

```python
from django import forms

from literature.ui.picker import ItemChoiceField


class ReviewForm(forms.Form):
    reference = ItemChoiceField()
```

On a model form, name the field in `Meta.field_classes` instead of declaring it. A field declared
on a model form is used exactly as written, so it would be required whatever the model field's
`blank` says and would lose the model field's `limit_choices_to`. Naming the class lets Django
build the field from the model field, as it does for any foreign key:

```python
from django import forms

from literature.ui.picker import ItemChoiceField

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["reference"]
        field_classes = {"reference": ItemChoiceField}
```

Here `Review.reference` is a `ForeignKey` to `literature.Item`. The field is required unless the
model field has `blank=True`, and a form opened on an existing record shows the reference already
chosen. Submitting a reference that has since been deleted gives the usual `invalid_choice` error.

The same field works on every row of an inline formset. Each row searches on its own.

## What the search matches

Typing narrows the choices to the references where the text appears in any one of:

- the title, anywhere in it
- the citation key, anywhere in it
- a contributor's family name, or the literal name of an organisation
- the DOI, with or without a `https://doi.org/` address or a `doi:` label in front, in any letter
  case

Case does not matter. Typing `%`, `_` or a quotation mark matches those characters and nothing
else. A reference that matches in several ways is offered once. A title or citation key that
starts with the text comes first, and at most 20 references are offered at a time. Each is shown
as its title (its citation key when it has no title), its year and its first author.

## Who may search

The search follows the catalogue list's read access, which is open to everyone. A reference the
search offers is already visible on the list, so it reveals nothing the list does not. To close it,
close the catalogue's read routes together by guarding the include where you mount them. The
search is closed along with the list and the reference pages, and the package has no separate
setting for it.
