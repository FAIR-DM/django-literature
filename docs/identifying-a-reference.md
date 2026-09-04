# Identifying a reference

Alongside a reference's own fields, the form the front end serves carries its identifiers as part of
the same page: a DOI, an ISBN, a URL, and the rest.

## Adding an identifier

Each identifier is one row: a kind and a value. The kinds the package knows are offered as you
type, and typing one in a different case, `isbn` instead of `ISBN`, is treated the same as
choosing it from the list. A kind the package does not know can be named too, and is stored exactly
as typed.

A reference holds at most one identifier of each kind. Adding a second of a kind it already has is
refused, with a message saying the reference already holds one of that kind, rather than a database
error.

## What gets checked, and what does not

The six known kinds are:

- DOI
- ISBN
- ISSN
- URL
- PMID
- PMCID

A value entered under one of these is checked against that kind's shape before it is stored. A kind
the package does not know is stored unchecked, whatever the value looks like, since there is
nothing for the package to check it against.

## Being told what is wrong

A rejected value is not stored, and the form says why. For most kinds, the message describes the
shape a valid value has. ISBN and ISSN are more specific: a value of the right shape whose check
digit does not add up is told apart from a value of the wrong shape entirely, since a mismatched
check digit is almost always a single mistyped character, and a well-formed example helps least
with exactly that mistake.

## Saving

Identifiers are saved together with the rest of the reference, in one submission. If anything on
the page is rejected, whether that is an invalid identifier, a repeated kind or anything else on
the form, none of it is stored, identifiers included. The page comes back with everything you
entered still in it.
