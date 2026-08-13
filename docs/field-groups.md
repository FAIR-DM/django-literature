# Field Groups in the Front End

The add and edit pages in `literature.ui` scope a reference's form to the fields its type
typically carries: choosing "Journal Article" reveals a different set of fields than choosing
"Map". This page documents where that mapping comes from, what it does and does not decide, and
how to raise a disagreement with it.

## It is presentation only, never storage

Nothing about which fields a reference *can* hold depends on this mapping. Every scalar field of
`Item` is part of the form on every page, always, and every value already stored survives a save
regardless of which fields the current type's groups happen to show. The mapping only decides
which fields are visible without asking. A field a reference's type does not usually carry is one
click away behind the form's "Show every field" toggle, and any field already holding a value is
shown automatically even if the current type would not otherwise offer it.

## CSL JSON has no such mapping

The [CSL JSON 1.0.2 specification](https://github.com/citation-style-language/schema) validates
every field against every type. There is no rule anywhere in its schema that ties a variable to a
particular item type. The specification text itself (Appendix III, item types, and Appendix IV,
variables) names a type for only a handful of variables, and no published source (from the
specification's own maintainers to any citation-management tool surveyed while this mapping was
built) offers a complete, reusable type-to-field table under a license this project can draw on.

This mapping is `literature.ui`'s own artefact, authored rather than derived, and every entry in
`literature/ui/fieldgroups.py` carries a one-line comment naming the reasoning that put it there.

## The groups

Every scalar field of `Item` (excluding the two JSON fields and the two timestamps, none of which
are on the form at all) belongs to exactly one of the following thirteen groups:

| Group | What it covers |
|---|---|
| Core | Type, citation key, title, abstract: shown for every reference, on every page |
| General | Note, annotation, keywords, language, status, source, call number: shown for every reference |
| Alternate titles | A short title, an original title, a part title, a volume title. No item type offers this group by default, so these fields are reached through the toggle |
| Container | The larger work a reference sits inside: a journal, a book, a collection |
| Publication | Publisher, place, edition, medium, genre, version |
| Original publication | The publisher and place of an earlier edition, for a republished or translated work |
| Numbering and pagination | Volume, issue, page range, chapter and section numbers |
| Event | The name and place of an event a reference records |
| Reviewed work | The title and genre of a work under review |
| Legal | Authority, jurisdiction, division and cross-references, for legal and legislative references |
| Archive | Where a physical or held item is kept |
| Physical description | Dimensions and scale |
| Processor-generated | Values a citation processor fills in, such as a citation label. Never offered by default, since no person enters them |

Every reference's form shows Core and General regardless of type. Every other group is shown only
for the types it is assigned to, and the assignment follows a fixed set of criteria: evidence from
the CSL specification text first, then a small number of narrower rules for cases the specification
does not name directly. The full per-type assignment, with the criterion behind each one recorded
beside it, lives in `literature.ui.fieldgroups`.

[Zotero's](https://www.zotero.org/) own item-type schema was used only as a plausibility check on
the *size* of each type's resulting set, never as a source: it carries no published license, and
nothing in this mapping is copied from it.

## Disagreeing with an entry

If a type's group assignment looks wrong, the comment beside that type in
`literature.ui.fieldgroups` names the reasoning it followed. Open an issue naming the type and
which part of that reasoning you think does not hold. That is a more useful starting point than
the mapping's conclusion on its own, since it is the reasoning a change would have to revisit.

## Attribution

The CSL specification text cited above is licensed
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) by the Citation Style Language
project.
