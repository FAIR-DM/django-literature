"""Move the variables a citation processor generates out of columns and into ``custom``.

A processor works these values out for one citation in one document, so they
describe no reference. Each stored value is kept in the item's ``custom`` data
under its CSL JSON name, where the converters read and write it (ADR 0035).
"""

from django.db import migrations

#: Column → the CSL JSON variable it held. Written out here rather than imported,
#: so the migration keeps meaning what it meant when the package code moves on.
COLUMNS = {
    "citation_label": "citation-label",
    "citation_number": "citation-number",
    "first_reference_note_number": "first-reference-note-number",
    "locator": "locator",
    "year_suffix": "year-suffix",
}


def into_custom(apps, schema_editor):
    """Copy every non-blank value into ``custom``, refusing a ``custom`` that is not an object."""
    Item = apps.get_model("literature", "Item")
    items = Item.objects.using(schema_editor.connection.alias)
    refused = []
    for item in items.exclude(**{column: "" for column in COLUMNS}).iterator():
        values = {key: getattr(item, column) for column, key in COLUMNS.items()}
        values = {key: value for key, value in values.items() if value}
        if not values:
            continue
        if item.custom is not None and not isinstance(item.custom, dict):
            refused.append(item.citation_key)
            continue
        item.custom = {**(item.custom or {}), **values}
        item.save(update_fields=["custom"])
    if refused:
        raise ValueError(
            "These items hold a citation-processor value but their custom data is "
            "not a JSON object, so the value has nowhere to go. Make custom an "
            "object or clear the value, then migrate again: " + ", ".join(refused)
        )


def out_of_custom(apps, schema_editor):
    """Move each value back into its column, clearing a ``custom`` left empty."""
    Item = apps.get_model("literature", "Item")
    items = Item.objects.using(schema_editor.connection.alias)
    for item in items.filter(custom__isnull=False).iterator():
        if not isinstance(item.custom, dict):
            continue
        held = {column: key for column, key in COLUMNS.items() if key in item.custom}
        if not held:
            continue
        for column, key in held.items():
            setattr(item, column, str(item.custom.pop(key)))
        item.custom = item.custom or None
        item.save(update_fields=[*held, "custom"])


class Migration(migrations.Migration):
    dependencies = [
        ("literature", "0003_alter_item_citation_key"),
    ]

    operations = [
        migrations.RunPython(into_custom, out_of_custom),
        *(
            migrations.RemoveField(model_name="item", name=column)
            for column in COLUMNS
        ),
    ]
