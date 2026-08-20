"""Search and filter definitions for the catalogue (plan.md D-1).

One module, imported by both presentations, so what is searchable and
filterable is declared once (FR-023) rather than restated per view.
"""

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
