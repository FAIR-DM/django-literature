# Crediting contributors

Alongside a reference's own fields, the form the front end serves carries its contributors —
authors, editors, translators and the rest of CSL JSON's 26 name-variable roles — as part of the
same page.

## Adding a contributor

Each contributor is one row: a role, a family name and a given name. Typing an organization or a
name that does not split into parts is fine too — leaving family and given blank and using the
unparsed name field records it as a single string instead, the way a publisher or a working group
is credited.

A row needs a family name or an unparsed name. Leaving both blank returns the form saying so, and
nothing is stored.

Less common parts of a name — particles such as "van" or "de", a suffix such as "Jr." or "III" —
sit off to the side rather than as two more columns every row carries. A person with a name they
apply to almost never leaves them alone; most rows never need them.

## Completion is a spelling aid, not a link

As you type a family name, the field offers names the catalogue already holds. Accepting one fills
in the text exactly as it is typed by hand — nothing about the reference is linked to the record the
suggestion came from. What gets stored is a new record carrying that text, every time, whether the
suggestion was accepted or the whole name was typed out.

This holds even when correcting a reference that already credits someone: editing a row's name
creates a new record if anything else in the catalogue is still credited under the old one, and
updates the existing record only when nothing else is. Either way, no other reference's contributor
list changes because of an edit made here.

The reason is not a missing feature. Nothing in a stored name can tell two people who happen to
share a spelling apart — a name carries no identifier of its own — so a control that appeared to
join two entries into one would be asserting something the catalogue has no way to know. Where
identity is genuinely ambiguous, creating a second record is the recoverable choice: it can be
joined later, once someone looks at the evidence and decides. Linking to the wrong person's record
by mistake cannot be undone the same way.

## Duplicates accumulate, and that is expected

Because entering a contributor never reuses a stored record, crediting the same person across many
references leaves many records behind — one per reference, not one per person. This is already true
of anything imported into the catalogue; entering references by hand does not create a new kind of
problem, it just means the same accumulation happens one row at a time instead of one file at a
time.

Joining records that turn out to name the same person is tracked separately, as
[issue #112](https://github.com/fairdm/django-literature/issues/112). It is not something this form
does.

## Reordering and removing

Contributors within one role can be reordered by changing the number beside each row. Numbers are
scoped to their own role — moving an author does not touch the editor list, and there is no single
list spanning every role to reorder across.

Removing a row takes the reference's credit away and nothing else. The contributor's own record
stays in the catalogue, still credited on whatever else it appears on, and still has its own page —
even one credited on nothing at all keeps a page, which then lists nothing.

## Saving

Contributors are saved together with the rest of the reference, in one submission. If anything on
the page is rejected — a missing contributor name, an invalid date, anywhere else on the form — none
of it is stored, contributors included, and the page comes back with everything you entered still in
it.
