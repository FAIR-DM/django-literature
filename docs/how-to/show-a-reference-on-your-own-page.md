# How to show a reference on your own page

Show a reference from the catalogue on one of your project's own pages, such as the publications
related to a dataset, with the same component the catalogue's own card list uses. You pass it one
`Item` and it shows:

- the title,
- the authors, or the editors marked "(ed.)" or "(eds.)" when the reference has no authors,
- the item type, the year it was issued, and the journal or book it appeared in with its volume,
  issue and pages, or its publisher when it appeared in neither,
- its DOI, as a link to `https://doi.org/`.

Up to ten names are listed, and any after the tenth are shortened to "et al.". A part the reference
does not hold is left out, so a reference with only a title shows only its title.

## Before you start

The component belongs to the front end, so the project needs `literature.ui` in `INSTALLED_APPS`
and django-cotton set up, as described in [Installing the front end](https://github.com/FAIR-DM/django-literature#installing-the-front-end) in the README. Mounting
the catalogue's URLs is optional. Without them, turn the links off, as described below.

## Show one reference

```html
<c-literature.item :item="reference" />
```

The title links to the reference's page in the catalogue, and each name links to that
contributor's page. The component draws no card or border of its own, so it fits into whatever
holds it: a card, a list row or a table cell.

## Show a list of references

Prefetch what the component reads, so the page costs the same number of queries however many
references it lists:

```python
references = dataset.related_literature.prefetch_related(
    "item_names__name", "item_dates", "item_identifiers"
)
```

```html
<c-list>
  {% for reference in references %}
    <c-list.row>
      <c-literature.item :item="reference" class="list-col-grow" />
    </c-list.row>
  {% endfor %}
</c-list>
```

Without the prefetch the component still renders, with a few queries per reference.

## Change what the component shows

| Attribute | Default | What it does |
|---|---|---|
| `item` | | The `literature.models.Item` to show. Required. |
| `level` | `3` | The heading level of the title. Set it to fit your page's outline, for example `level="4"` under an `h3` section. |
| `href` | the reference's catalogue page | Where the title links to, for example your own page about the reference. |
| `link` | `True` | Whether the title and names are links. Pass `:link="False"` when the catalogue's URLs are not mounted, because the reference's catalogue page cannot be found there. |
| `abstract` | `False` | Show the first thirty words of the abstract under the reference. |
| `class` | | Extra classes on the component's outer element. |

Anything you put between the opening and closing tags is shown under the reference:

```html
<c-literature.item :item="reference">
  <c-mvp.text size="sm" muted tight>{% translate "Cited in chapter 3" %}</c-mvp.text>
</c-literature.item>
```

## Change the catalogue's own card

The catalogue's card list wraps the component in a card, with the abstract and the citation key.
That card is `literature/ui/item_list_item.html`. To change it, for example to list every
contributor role on the card, put a template with the same path in your project's template
directory. Django finds yours first.
