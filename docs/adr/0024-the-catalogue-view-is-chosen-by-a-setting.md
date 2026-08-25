# ADR 0024 — The catalogue view is chosen by a setting, not by routing

**Status:** accepted

## Decision

The catalogue route is `literature:item-list`, it serves the table, and a project that wants a
different view names one under the namespaced `LITERATURE` setting:

```python
LITERATURE = {"CATALOGUE_VIEW": "literature.ui.views.ItemListView"}
```

The value is a dotted path to a view class, not a switch between two names the package knows about.
It is resolved when the request arrives, not when the module is imported. A path that does not
import, or that imports to something which cannot serve a request, raises `ImproperlyConfigured`
naming the setting.

The route itself is fixed. It is the only route in the front end whose view a project chooses; every
other one is the package's.

## Why

The obvious alternative — let a project route the catalogue at whichever view it wants — does not
work here, and the reason is structural rather than stylistic. Every route in this app is registered
through one `include()` under one namespace. A project that adds a second `include()` to override a
single route breaks `reverse()` for the rest of them, so a breadcrumb back to the catalogue, a
create form's success URL, and the delete page's decline path all stop resolving. The failure is not
at the route that was overridden; it is everywhere else, which makes it expensive to diagnose.

So the choice has to be made behind the name rather than by moving the name. That keeps
`literature:item-list` meaning "the catalogue" for every other piece of the app, whichever view is
serving it.

**A dotted path rather than a two-value switch**, for the same reason `BIB_FORMATS` takes one. A
project that has subclassed either view — to add a column, change a page size, narrow the
queryset — can name its own class and keep every other route, breadcrumb and redirect pointing at
the same name. A boolean would force that project back to overriding the route, which is the thing
this decision exists to avoid.

**Resolved per request rather than at import time** for two reasons. Reading settings at import time
makes the app's behaviour depend on whether the host's `urls.py` ran before or after it configured
settings, which is a genuine ordering hazard in a reusable app. And it makes the choice testable
with `override_settings`, which is what lets the package assert that both presentations work rather
than only the default.

**Validation happens at the setting, not at the failure.** A bad dotted path surfacing as an
`AttributeError` from inside URL resolution puts the error a long way from the line that caused it.
The package already validates the shape of the `LITERATURE` dict this way for its format registry,
so this follows an established local convention rather than inventing one.

## Consequences

- A project upgrading into the release that made the table the default sees its catalogue change,
  and restores the previous page by adding one setting rather than by forking a template or a URL
  list.
- The card list stays a supported, documented, tested view rather than surviving as dead code. The
  contributor page goes on using it, so it stays exercised by the suite.
- The package gains one configuration key. It is namespaced under the key the package already owns,
  so it adds no new top-level setting.
- A future third presentation costs a class and a documentation line, with no change here.

## Alternatives rejected

**Rename the classes so the table takes `ItemListView`.** Tidier to read, and it silently changes
what every downstream import already resolves to, including anything that subclassed it. The name a
project already depends on keeps meaning what it meant.

**Ship both routes and let the project pick a URL.** Two addresses for the catalogue means two
addresses in bookmarks and links, and the app would still have to decide which one its own
breadcrumbs point at — which is this decision again, unmade.

**Deprecate the card list.** It is the presentation a public-facing reading list wants, and removing
it would say the opposite of what the change of default was for.
