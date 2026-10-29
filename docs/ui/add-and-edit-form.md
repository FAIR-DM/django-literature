# Add and edit form

The form the web interface's add and edit pages share, `literature.ui.forms.ItemForm` with its
contributor and identifier sets. It has four tabs: Reference, Contributors, Identifiers and More.
Why a reference's type decides which sections are shown is explained
[below](#why-the-form-shows-different-fields-for-each-type).

## Sections

Every scalar field of `Item` belongs to one of twelve groups, except the two JSON fields and the
two timestamps, which are not on the form. Core and General are shown for every reference. Every
other group is shown for the types `literature.ui.fieldgroups` assigns it to.

| Group | What it covers |
|---|---|
| Core | Type, citation key, title, abstract: shown for every reference, on every page |
| General | Note, annotation, keywords, language, status, source, call number: shown for every reference, the notes and catalogue fields on the More tab |
| Alternate titles | A short title, an original title, a part title, a volume title. On the More tab for every type |
| Published in | The larger work a reference sits inside: a journal, a book, a collection |
| Publication | Publisher, place, edition, medium, genre, version |
| Original publication | The publisher and place of an earlier edition, for a republished or translated work |
| Numbering and pagination | Volume, issue, page range, chapter and section numbers |
| Event | The name and place of an event a reference records |
| Reviewed work | The title and genre of a work under review |
| Legal | Authority, jurisdiction, division and cross-references, for legal and legislative references |
| Archive | Where a physical or held item is kept |
| Physical description | Dimensions and scale |

"Show sections other types use" shows every group. A field that already holds a value is shown
whatever the reference's type.

## Dates

Each of CSL JSON's six date slots is a field in the Dates section of the Reference tab:

| Field | CSL JSON slot |
|---|---|
| Submitted | `submitted` |
| Published | `issued` |
| Available online | `available-date` |
| Event date | `event-date` |
| Originally published | `original-date` |
| Accessed | `accessed` |

- **Precision.** A date is a year, then optionally a month, then optionally a day. A year alone
  stores a year-only date, a year and a month store both, and all three store a full date. A
  stored date is shown at the precision it was entered at.
- **Spans.** An event date can take an end date. The two ends can hold different precisions. Any
  other slot already holding a span shows its end date too. An end date without a start, or one
  before its start, is refused with a message.
- **Which slots are shown.** Published is always shown. The slots typical for the reference's type
  are shown beside it: Available online for a journal article, Accessed for a webpage, Event date
  for a conference paper. A slot that already holds a value is always shown, and changing the type
  never drops a date. "Show sections other types use" shows every slot.
- **Imported text.** A date imported as text that could not be read as a date shows that text in
  place of the date. Typing a date over it stores the date. The text stays in the record either
  way.
- **Clearing.** Emptying a slot's field removes its date and touches no other slot. Text kept from
  an import stays.

## Contributors tab

One list for each of CSL JSON's 26 name roles, each under its own heading. A name's role is the
list it is entered in.

- **Which roles are listed.** Authors are always listed. Beside them are the roles the reference's
  type usually credits, such as editors and translators for a book or a director and a producer
  for a film, and any role that already holds a name. "Show other roles" lists the rest.
- **A row.** A family name and a given name. "An organisation", in the row's name details, takes
  one name recorded as a single string instead, for a publisher or a working group. The name
  details also hold the particles, such as "van" or "de", and the suffixes, such as "Jr." or "III".
  A dot on the name details button shows that a row holds one.
- **Required.** A row needs a family name or an organisation name. A row with neither is refused
  with a message.
- **Completion.** Typing a family name offers names the catalogue already holds. Accepting one
  fills in the text. The row is saved as a new name record, whether the text was accepted or
  typed. Editing a credited name creates a new record when anything else is credited under the old
  one, and updates the record when nothing else is. See
  [Why a contributor is never linked to an existing record](#why-a-contributor-is-never-linked-to-an-existing-record).
- **Order.** Contributors are credited in the order their list shows them. Each row's move up and
  move down buttons change that order, within its own role only.
- **Removing.** Removing a row removes the reference's credit only. The name record stays in the
  catalogue with its own page, even when it is credited on nothing.

## Identifiers tab

One row for each identifier: a type and a value.

- **Type.** Chosen from the six known types: DOI, ISBN, ISSN, URL, PMID and PMCID. A known type
  typed in another case, `isbn` for `ISBN`, is the same type. Any other type, such as arXiv or
  Handle, can be typed in and is stored as typed.
- **One of each type.** A reference holds at most one identifier of each type. A second of a type
  it already holds is refused with a message.
- **Checking.** A value of a known type is checked against that type's shape before it is stored.
  A value of any other type is stored unchecked.
- **Messages.** A rejected value is not stored, and the message describes the shape a valid value
  has. For ISBN and ISSN, a value of the right shape whose check digit does not add up gets a
  message of its own.

## More tab

Notes, annotation, alternate titles, source and call number.

## Saving

The reference, its dates, its contributors and its identifiers are saved in one submission. If
anything on the page is refused, nothing is stored, and the page comes back with every error
listed above the tabs and everything entered still in it.

Adding needs the `literature.add_item` permission and editing needs `literature.change_item`.

## Why the form shows different fields for each type

The form scopes a reference to the fields its type typically carries: choosing "Journal Article"
shows a different set of fields than choosing "Map". This section covers where that mapping comes
from, what it does and does not decide, and how to raise a disagreement with it.

### It is presentation only, never storage

Nothing about which fields a reference *can* hold depends on this mapping. Every scalar field of
`Item` is part of the form on every page, always, and every value already stored survives a save
regardless of which fields the current type's groups happen to show. The mapping only decides
which fields are visible without asking. A section a reference's type does not usually carry is one
click away behind the form's "Show sections other types use" toggle, and any field already holding
a value is shown automatically even if the current type would not otherwise offer it.

### CSL JSON has no such mapping

The [CSL JSON 1.0.2 specification](https://github.com/citation-style-language/schema) validates
every field against every type. There is no rule anywhere in its schema that ties a variable to a
particular item type. The specification text itself (Appendix III, item types, and Appendix IV,
variables) names a type for only a handful of variables, and no published source (from the
specification's own maintainers to any citation-management tool surveyed while this mapping was
built) offers a complete, reusable type-to-field table under a license this project can draw on.

This mapping is `literature.ui`'s own artefact, authored rather than derived, and every entry in
`literature/ui/fieldgroups.py` carries a one-line comment naming the reasoning that put it there.

### How a group is assigned to a type

Core and General are shown for every reference. Every other group is shown only for the types it is
assigned to, and the assignment follows a fixed set of criteria: evidence from the CSL
specification text first, then a small number of narrower rules for cases the specification does
not name directly. The full per-type assignment, with the criterion behind each one recorded beside
it, lives in `literature.ui.fieldgroups`.

[Zotero's](https://www.zotero.org/) own item-type schema was used only as a plausibility check on
the *size* of each type's resulting set, never as a source: it carries no published license, and
nothing in this mapping is copied from it.

### Disagreeing with an entry

If a type's group assignment looks wrong, the comment beside that type in
`literature.ui.fieldgroups` names the reasoning it followed. An issue naming the type and the part
of that reasoning that does not hold is a more useful starting point than the mapping's conclusion
on its own, since it is the reasoning a change would have to revisit.

### Attribution

The CSL specification text cited above is licensed
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) by the Citation Style Language
project.

## Why a contributor is never linked to an existing record

A contributor is stored as a name record, credited on a reference in a role. Entering a
contributor on this form never links to a record the catalogue already holds. How names and roles
are modelled is recorded in [ADR 0003](../adr/0003-names-are-role-neutral-and-shared.md).

### Completion is a spelling aid, not a link

As you type a family name, the form offers names the catalogue already holds. Accepting one fills
in the text exactly as typing it would. Nothing about the reference is linked to the record the
suggestion came from: what gets stored is a new record carrying that text. The same holds when a
credited name is corrected. No other reference's contributor list changes because of an edit on
this one.

A stored name carries no identifier of its own, so nothing in it can tell two people who share a
spelling apart. A control that appeared to join two entries into one would be asserting something
the catalogue has no way to know. Where identity is ambiguous, a second record is the recoverable
choice: it can be joined later, once someone looks at the evidence and decides. Linking to the
wrong person's record cannot be undone the same way. The decision is recorded in
[ADR 0031](../adr/0031-completion-suggests-a-spelling-never-a-record.md).

### Duplicates accumulate, and that is expected

Because entering a contributor never reuses a stored record, crediting the same person on many
references leaves many records behind: one per reference, not one per person. Importing a file
already does the same. Entering references by hand adds no new kind of problem. The same
accumulation happens one row at a time instead of one file at a time.

Joining records that turn out to name the same person is tracked as
[issue 112](https://github.com/FAIR-DM/django-literature/issues/112). The form does not do it.
