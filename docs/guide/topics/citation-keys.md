# Citation keys

A citation key is the short name a reference is cited by in a manuscript, such as `Jennings2019`.
This page covers why the package stores a key exactly as it arrives and never keeps keys distinct.
How the BibTeX and RIS importers find or make a key is in their mappings,
[BibTeX](../../reference/bibtex-mapping.md) and [RIS](../../reference/ris-mapping.md).

## A key is stored as given

`from_csl_json()`, the file importers and the front end's forms all store a key exactly as it
arrives. If a reference with the same key already exists, the new one is stored under that key
too. Nothing warns, nothing refuses, and nothing rewrites the key to keep the two apart. Existing
records are never overwritten.

## Keeping keys distinct is the reader's business

`citation_key` is not declared unique, and two references may share a key. A key exists so a
person can point at the right reference in their own manuscript, so keeping keys distinct is their
business, as it is in every other reference manager.

Enforcing it would also go wrong. A check across the whole store assumes one bibliography per
installation, which separate bibliographies per user, or per article being written, would break.
And rewriting a clashing key, as the package once did by storing `smith2020` as `smith2020-2`,
quietly changes the key the person cites. The decision is recorded in
[ADR 0023](../../adr/0023-citation-key-uniqueness-is-the-readers-concern.md).

## A reference is addressed by its primary key

Because a key may be shared, it does not pick out one reference. A reference's page in the
catalogue is addressed by its primary key for this reason
([ADR 0015](../../adr/0015-a-reference-page-is-addressed-by-primary-key.md)).
`Item.objects.get(citation_key=...)` can raise `MultipleObjectsReturned`, so a lookup by key uses
`filter()` wherever a duplicate is possible.
