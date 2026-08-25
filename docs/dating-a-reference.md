# Dating a reference

Alongside a reference's own fields, the form the front end serves carries its dates as part of the
same page: issued, accessed, submitted and the rest of CSL JSON's six date-variable slots.

## Entering a date

A date can be typed as a year alone, a year and month, or a full date, whichever precision you
actually know. Nothing declares the precision up front. Typing `1998` stores a year-only date,
`1998-03` stores a year and month, and `1998-03-14` stores a full date. A stored date is shown back
at the same precision it was entered at.

A span is entered by giving a second, later date to end it. The two ends can hold different
precisions, so a year-only start and a full end date are both valid together. An end date given
without a start, or one that falls before its own start, is refused with a message rather than
stored.

## Which dates are on the page already

The publication date (`issued`) is always on the page. Alongside it, a reference already shows a
row for whichever other slots are typical for its own kind. A journal article, for instance,
shows a row for its online availability date as well, since that is common for the type. This is a
starting point, not a limit: it decides what is offered without your having to look for it, never
what can actually be stored.

A slot that already holds a value is always shown, whatever the reference's type. Changing a
reference's type on this same page never drops a date it already has, even one that type would not
have shown by default.

## Reaching a less common slot

Every one of the six slots is reachable without leaving the form, whether or not it is one of the
ones already showing. Adding a row offers a choice of whichever slots are not already on the page,
so the same slot is never offered twice. Once a row's slot is chosen and the date is saved, that
row's slot is settled and behaves the same as any other.

## Repairing an imported date

A reference imported from a file that could not be parsed into a structured date sometimes keeps
the original text instead of losing it outright. Where that is the case, the text is shown in place
of the date it stands in for, so it can be read and, if the actual date is known, replaced by typing
a real one over it. Replacing it stores the readable date. The original text stays in the record
either way.

## Clearing a date

Removing a date takes it out of that slot and nothing else. No other slot is affected, and the
slot itself becomes reachable again the way any other unused one is.

## Saving

Dates are saved together with the rest of the reference, in one submission. Two rows both naming
the same slot are refused with a message naming the slot, before anything is stored. If anything on
the page is rejected, whether that is an invalid date, a duplicated slot or anything else on the
form, none of it is stored, dates included. The page comes back with everything you entered still
in it.
