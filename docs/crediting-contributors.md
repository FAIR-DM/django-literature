# Crediting contributors

The form the front end serves gives a reference's contributors a tab of their own: authors,
editors, translators and the rest of CSL JSON's 26 name-variable roles.

## One list per role

Each role is its own list, under its own heading, so a name's role is the list it is entered in.
Authors are always listed. The roles the reference's type usually credits are listed beside them,
editors and translators for a book, say, or a director and a producer for a film, and so is any role
that already holds a name. "Show other roles" lists the rest. Like the type's field sections, this
decides what is offered without looking for it, never what can be stored.

## Adding a contributor

Each contributor is one row: a family name and a given name. An organisation, or a name to print
exactly as written, is entered by opening the row's name details and choosing "An organisation".
The row then takes one name, recorded as a single string, the way a publisher or a working group is
credited.

A row needs a family name or an organisation name. Leaving both blank returns the form saying so,
and nothing is stored.

The less common parts of a name sit in the row's name details rather than as more columns on every
row. Those are the particles, such as "van" or "de", and the suffixes, such as "Jr." or "III". A
dot on the name details button shows that a row holds one.

## Completion is a spelling aid, not a link

As you type a family name, the field offers names the catalogue already holds. Accepting one fills
in the text exactly as typing it by hand would. Nothing about the reference is linked to the record
the suggestion came from. What gets stored is a new record carrying that text, every time, whether
the suggestion was accepted or the whole name was typed out.

This holds even when correcting a reference that already credits someone. Editing a row's name
creates a new record if anything else in the catalogue is still credited under the old one, and
updates the existing record only when nothing else is. Either way, no other reference's contributor
list changes because of an edit made here.

The reason is not a missing feature. Nothing in a stored name can tell two people who happen to
share a spelling apart, since a name carries no identifier of its own, so a control that appeared to
join two entries into one would be asserting something the catalogue has no way to know. Where
identity is genuinely ambiguous, creating a second record is the recoverable choice. It can be
joined later, once someone looks at the evidence and decides. Linking to the wrong person's record
by mistake cannot be undone the same way.

## Duplicates accumulate, and that is expected

Because entering a contributor never reuses a stored record, crediting the same person across many
references leaves many records behind: one per reference, not one per person. This is already true
of anything imported into the catalogue. Entering references by hand does not create a new kind of
problem, it just means the same accumulation happens one row at a time instead of one file at a
time.

Joining records that turn out to name the same person is tracked separately, as
[issue #112](https://github.com/fairdm/django-literature/issues/112). It is not something this form
does.

## Reordering and removing

Contributors are credited in the order their role's list shows them. Each row's move up and move
down buttons change that order. Each role's list has its own order, so moving an author does not
touch the editors.

Removing a row takes the reference's credit away and nothing else. The contributor's own record
stays in the catalogue, still credited on whatever else it appears on, and still has its own page.
Even a record credited on nothing at all keeps a page, which then lists nothing.

## Saving

Contributors are saved together with the rest of the reference, in one submission. If anything on
the page is rejected, whether that is a missing contributor name, an invalid date or anything else
on the form, none of it is stored, contributors included. The page comes back with everything you
entered still in it.
