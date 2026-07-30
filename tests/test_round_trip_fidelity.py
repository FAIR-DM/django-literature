"""Full-item round-trip fidelity test (US2 — Convert Between Model and CSL JSON).

SC-002 in spec 001 asks for identical field values across a reference set of
test fixtures covering all item types and every CSL JSON date form. The
individual pieces are covered elsewhere in ``tests/test_converters.py``
(per-form date round-trips, name parts, identifier placement, a type-only
round-trip over all 45 item types, and one real-world fixture), but no single
test round-trips a fully populated item and asserts the whole field set comes
back unchanged. This module fills that gap.
"""

import pytest
from partial_date import PartialDate

from literature.choices import DateType, IdentifierType, ItemType, NameRole
from literature.converters import from_csl_json, to_csl_json
from literature.models import Item, ItemDate, ItemIdentifier, ItemName
from tests.factories import ItemDateFactory, ItemFactory, ItemIdentifierFactory, ItemNameFactory, NameFactory


def _item_scalar_field_names() -> list[str]:
    """Every Item field that to_csl_json() treats as a plain scalar column.

    Mirrors the skip set in ``to_csl_json()`` so this list tracks the model
    automatically as fields are added, instead of a hand-maintained duplicate.
    """
    skip = {"id", "pk", "citation_key", "type", "categories", "custom", "created", "modified"}
    return [f.name for f in Item._meta.get_fields() if hasattr(f, "attname") and f.name not in skip]


@pytest.mark.django_db
class TestRoundTripFidelity:
    """Full-item round trip: model -> CSL JSON -> model preserves the whole field set.

    Builds one fully populated item — every scalar field, contributors across
    several roles, every CSL date form, and a set of identifiers — and asserts
    the whole field set comes back unchanged (SC-002).
    """

    def test_full_item_round_trip_preserves_every_field(self):
        """A fully populated item survives a to_csl_json/from_csl_json cycle."""
        # Every scalar field gets its own field name as the value: short,
        # collision-free, and self-documenting on a mismatch.
        scalar_kwargs = {name: name for name in _item_scalar_field_names()}
        scalar_kwargs["year_suffix"] = "a"  # field name itself overflows max_length=10

        original = ItemFactory(
            citation_key="FullRoundTrip",
            type=ItemType.ARTICLE_JOURNAL,
            categories=["physics", "geophysics"],
            **scalar_kwargs,
        )

        # Contributors across several roles, including a fully detailed name
        # and a literal (organization) name.
        author_one = NameFactory(family="Alpha", given="Ada")
        author_two = NameFactory(family="Beta", given="Bao")
        editor = NameFactory(
            family="García",
            given="José",
            dropping_particle="de",
            non_dropping_particle="la",
            suffix="Jr.",
            comma_suffix=True,
            static_ordering=True,
            parse_names=True,
        )
        translator = NameFactory(family="", given="", literal="World Health Organization")
        ItemNameFactory(item=original, name=author_one, role=NameRole.AUTHOR)
        ItemNameFactory(item=original, name=author_two, role=NameRole.AUTHOR)
        ItemNameFactory(item=original, name=editor, role=NameRole.EDITOR)
        ItemNameFactory(item=original, name=translator, role=NameRole.TRANSLATOR)

        # Every CSL date form, one per date-variable slot: year-only,
        # year-month, full date, full date range, partial date range, and a
        # literal/season/circa date with no date-parts at all.
        ItemDateFactory(item=original, date_type=DateType.ORIGINAL_DATE, begin=PartialDate("2015"))
        ItemDateFactory(item=original, date_type=DateType.ACCESSED, begin=PartialDate("2020-03"))
        ItemDateFactory(item=original, date_type=DateType.ISSUED, begin=PartialDate("2019-08-16"))
        ItemDateFactory(
            item=original,
            date_type=DateType.EVENT_DATE,
            begin=PartialDate("2019-08-12"),
            end=PartialDate("2019-08-16"),
        )
        ItemDateFactory(
            item=original,
            date_type=DateType.AVAILABLE_DATE,
            begin=PartialDate("2021"),
            end=PartialDate("2021-06-30"),
        )
        ItemDateFactory(
            item=original,
            date_type=DateType.SUBMITTED,
            begin=None,
            literal="Summer 2019",
            season="Summer",
            circa=True,
        )

        # A set of identifiers: several known top-level types plus one
        # unknown type routed through the custom object.
        ItemIdentifierFactory(item=original, type=IdentifierType.DOI, value="10.1234/full-round-trip")
        ItemIdentifierFactory(item=original, type=IdentifierType.ISBN, value="978-3-16-148410-0")
        ItemIdentifierFactory(item=original, type=IdentifierType.ISSN, value="0956-540X")
        ItemIdentifierFactory(item=original, type="arXiv", value="2103.12345")

        exported = to_csl_json(original)
        exported["citation-key"] = "FullRoundTrip_reimported"
        reimported = from_csl_json(exported)

        # Scalar fields, plus type and categories.
        for name in _item_scalar_field_names():
            assert getattr(reimported, name) == getattr(original, name), name
        assert reimported.type == original.type
        assert reimported.categories == original.categories

        # Contributors: same roles, same order within each role, same name parts.
        def _name_signature(for_item):
            return [
                (n.role, n.order, n.name.family, n.name.given, n.name.literal)
                for n in ItemName.objects.filter(item=for_item).order_by("role", "order")
            ]

        assert _name_signature(reimported) == _name_signature(original)

        # Dates: same slot, same begin/end/literal/season/circa.
        def _date_signature(for_item):
            return {
                d.date_type: (
                    str(d.begin) if d.begin is not None else None,
                    str(d.end) if d.end is not None else None,
                    d.literal,
                    d.season,
                    d.circa,
                )
                for d in ItemDate.objects.filter(item=for_item)
            }

        assert _date_signature(reimported) == _date_signature(original)

        # Identifiers: same (type, value) set.
        def _identifier_signature(for_item):
            return {(i.type, i.value) for i in ItemIdentifier.objects.filter(item=for_item)}

        assert _identifier_signature(reimported) == _identifier_signature(original)
