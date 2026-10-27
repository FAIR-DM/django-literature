# ADR 0037 — The reference picker is a django-tomselect field

**Status:** accepted

## Decision

The front end's reference picker is built on django-tomselect.

- `ReferenceField` and `ReferenceMultipleField` subclass django-tomselect's model choice fields
  and add one thing: a default configuration naming the package's search view, so a project
  declares one field and writes no view, route or script.
- The search view subclasses django-tomselect's `AutocompleteModelView`. It is open to everyone,
  like the catalogue list (ADR 0036).
- A picker is restricted with django-tomselect's `filter_by` and `exclude_by` conditions. The
  fields apply a restriction's constant conditions again when they validate a submission, because
  django-tomselect validates against its view's unrestricted queryset.
- The package ships no widget and no script of its own for the picker.

django-tomselect is a dependency of the `ui` extra.

## Why

django-mvp-forms already draws django-tomselect's widgets in its forms, and django-tomselect already
provides everything a picker needs: an autocomplete view, fields that find it by URL name,
filter conditions, and the script that loads matches and shows the chosen references. Building the
same pieces again on a plain Tom Select widget meant a script, a widget and a restriction mechanism
of our own to maintain, and a second way of doing what the forms package already supports.

The restriction is checked again on submit because django-tomselect's conditions arrive as request
parameters and only narrow the search. A form that accepted any reference whatever the picker
offered would let a hand-made request save one outside it.

## Revisit if

django-tomselect validates a submission against its configured conditions itself, at which point
the fields' own check can go, or django-mvp-forms stops supporting django-tomselect.
