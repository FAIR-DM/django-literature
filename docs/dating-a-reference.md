# Dating a reference

The form the front end serves gives each of CSL JSON's six date slots a field of its own, in the
Dates section of the Reference tab:

| Field | CSL JSON slot |
|---|---|
| Submitted | `submitted` |
| Published | `issued` |
| Available online | `available-date` |
| Event date | `event-date` |
| Originally published | `original-date` |
| Accessed | `accessed` |

## Entering a date

A date is a year, then optionally a month, then optionally a day, whichever precision you actually
know. A year alone stores a year-only date, a year and a month store both, and all three store a
full date. A stored date is shown back at the same precision it was entered at.

An event date can be a span: give an end date as well. The two ends can hold different precisions,
so a year-only start and a full end date are both valid together. Any other slot already holding a
span shows its end date too. An end date given without a start, or one that falls before its own
start, is refused with a message rather than stored.

## Which dates are on the page

Published is always on the page. Alongside it, the form shows whichever other slots are typical for
the reference's type: a journal article shows Available online, a webpage shows Accessed, a
conference paper shows Event date. "Show sections other types use" shows every slot. This decides
what is offered without looking for it, never what can be stored.

A slot that already holds a value is always shown, whatever the reference's type. Changing a
reference's type never drops a date it already has, even one that type would not have shown.

## Repairing an imported date

A reference imported from a file that could not be parsed into a structured date sometimes keeps
the original text instead of losing it outright. Where that is the case, the text is shown in place
of the date it stands in for, so it can be read and, if the actual date is known, replaced by typing
a real one over it. Replacing it stores the readable date. The original text stays in the record
either way.

## Clearing a date

Emptying a slot's field takes its date away and touches no other slot. A slot that also holds the
original text of an imported date keeps that text, so emptying the field never loses it.

## Saving

Dates are saved together with the rest of the reference, in one submission. If anything on the page
is rejected, whether that is an invalid date or anything else on the form, none of it is stored,
dates included. The page comes back with everything you entered still in it.
