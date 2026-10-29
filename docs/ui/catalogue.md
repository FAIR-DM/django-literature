# The catalogue

The web interface's catalogue lists every stored reference, with a page for each reference and each
contributor, and pages to add, edit, delete and import references. It is live as soon as the
web interface's URLs are mounted, as described in [Installing the web interface](installation.md).

## Choose the table or the cards

By default the catalogue is a table: one row per reference, showing its citation key, item type,
title, the journal or book it appeared in, its credited names and its issued date. Every column
but the names can be sorted. A row's title opens the reference's page.

A project building a public reading list rather than a tool for managing one can show the
catalogue as cards instead, one reference per card:

```python
# settings.py
LITERATURE = {
    "CATALOGUE_VIEW": "literature.ui.views.ItemListView",
}
```

The value is a dotted path, so a subclass of either view, with a column added, a different page
size or a narrower queryset, can be named here instead. The route keeps the name
`literature:item-list` either way. A contributor's page always lists their works as cards. The
setting is described in [Settings](../reference/settings.md).

## Search and filter

Both presentations carry a search box and three filters, from one shared definition, so a narrowed
catalogue returns the same references whichever view serves it. On the table they sit together in
the toolbar. On the cards the filters open in a drawer from a **Filters** button.

The search box matches part of a word, in any case, against a reference's citation key, its title,
short title and original title, the journal or book it appeared in, and every contributor's name.
It does not search abstracts or keywords.

The filters narrow on:

- **Type**: the kind of reference, such as an article, a book or a dataset. Several can be ticked.
- **Year**: the year the issued date falls in, newest first. A reference with no issued date never
  matches.
- **Language**: the languages the catalogue holds.

Several values in one filter widen it: an article or a book. A search and a filter, or two filters,
narrow it: an article, published in 2019. There is no contributor filter. To find everything a
person is credited on, search their name.

The search, the filters, the sort and the page are all held in the address, so a bookmarked
catalogue reopens exactly as it was.

## Add, edit and delete references

The catalogue carries an **Add** action, and a reference's page carries **Edit** and **Delete**.
The form is laid out in four tabs:

- **Reference**: the type, citation key and title, the sections the chosen type uses, the dates,
  and the abstract and keywords.
- **Contributors**: one list per role.
- **Identifiers**: a DOI, an ISBN, a URL and any other identifier.
- **More**: notes, an annotation, alternate titles and where the reference was catalogued.

Choosing a type shows only the sections, dates and roles that kind of reference usually carries,
with toggles to show the rest. Nothing is dropped by choosing a narrower type. Why the form works
this way is explained in [Field groups](../topics/field-groups.md), and every field is listed in
[Add and edit form](add-and-edit-form.md).

To import references from a file instead, see
[Importing a file](import-pages.md).

## Control who can change the catalogue

Each page that changes the catalogue requires a model permission:

| Page | Permission |
|---|---|
| Add, Import | `literature.add_item` |
| Edit | `literature.change_item` |
| Delete | `literature.delete_item` |

A visitor who is not signed in is sent to your `LOGIN_URL`, and a signed-in user without the
permission is refused. An action is only shown to users who hold its permission. Grant the three
permissions to a group for the people who maintain the catalogue.

The catalogue list, reference pages and contributor pages are open to everyone. To apply another
rule, subclass the view and set `permission_required` or override `has_permission()`.
