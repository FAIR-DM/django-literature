# Contributor records

A contributor is stored as a name record, credited on a reference in a role. This page covers why
entering a contributor on the [add and edit form](../../reference/add-and-edit-form.md) never links to
a record the catalogue already holds, and what that leaves behind. How names and roles are modelled
is recorded in [ADR 0003](../../adr/0003-names-are-role-neutral-and-shared.md).

## Completion is a spelling aid, not a link

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
[ADR 0031](../../adr/0031-completion-suggests-a-spelling-never-a-record.md).

## Duplicates accumulate, and that is expected

Because entering a contributor never reuses a stored record, crediting the same person on many
references leaves many records behind: one per reference, not one per person. Importing a file
already does the same. Entering references by hand adds no new kind of problem. The same
accumulation happens one row at a time instead of one file at a time.

Joining records that turn out to name the same person is tracked as
[issue 112](https://github.com/FAIR-DM/django-literature/issues/112). The form does not do it.
