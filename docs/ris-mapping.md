# RIS mapping

What this package makes of a `.ris` file: which reference type becomes which CSL item
type, and which tag becomes which CSL variable, contributor role, date or identifier. One
format reads EndNote, Web of Science and Scopus alike — there is no producer detection, so
every row below is resolved from the tag itself, never from which tool wrote the file.

This page is generated from the mapping tables themselves, so it cannot describe something
the importer does not do. A tag with no row here is not discarded: it is kept with the
record under `custom["ris"]`, where it can be read back afterwards.

## Reference types

| RIS `TY` | CSL item type |
| --- | --- |
| `ABST` | `article-journal` |
| `ADVS` | `motion_picture` |
| `AGGR` | `dataset` |
| `ANCIENT` | `classic` |
| `ART` | `graphic` |
| `BILL` | `bill` |
| `BLOG` | `post-weblog` |
| `BOOK` | `book` |
| `CASE` | `legal_case` |
| `CHAP` | `chapter` |
| `CHART` | `graphic` |
| `CLSWK` | `classic` |
| `COMP` | `software` |
| `CONF` | `paper-conference` |
| `CPAPER` | `paper-conference` |
| `CTLG` | `document` |
| `DATA` | `dataset` |
| `DBASE` | `dataset` |
| `DICT` | `entry-dictionary` |
| `EBOOK` | `book` |
| `ECHAP` | `chapter` |
| `EDBOOK` | `book` |
| `EJOUR` | `article-journal` |
| `ELEC` | `webpage` |
| `ENCYC` | `entry-encyclopedia` |
| `FIGURE` | `figure` |
| `GEN` | `document` |
| `GOVDOC` | `legislation` |
| `GRANT` | `document` |
| `GRNT` | `document` |
| `HEAR` | `hearing` |
| `ICOMM` | `personal_communication` |
| `INPR` | `article-journal` |
| `JFULL` | `periodical` |
| `JOUR` | `article-journal` |
| `LEGAL` | `legislation` |
| `MANSCPT` | `manuscript` |
| `MAP` | `map` |
| `MGZN` | `article-magazine` |
| `MPCT` | `motion_picture` |
| `MULTI` | `webpage` |
| `MUSIC` | `musical_score` |
| `NEWS` | `article-newspaper` |
| `PAMP` | `pamphlet` |
| `PAT` | `patent` |
| `PCOMM` | `personal_communication` |
| `RPRT` | `report` |
| `SER` | `periodical` |
| `SLIDE` | `graphic` |
| `SOUND` | `song` |
| `STAND` | `standard` |
| `STAT` | `legislation` |
| `THES` | `thesis` |
| `UNBILL` | `bill` |
| `UNPB` | `manuscript` |
| `UNPD` | `manuscript` |
| `VIDEO` | `motion_picture` |

A reference type with no row above becomes `document` rather than failing the entry.

## Tags

| RIS tag | CSL variable |
| --- | --- |
| `AB` | `abstract` |
| `CY` | `publisher-place` |
| `ET` | `edition` |
| `IS` | `issue` |
| `LA` | `language` |
| `M3` | `genre` |
| `PB` | `publisher` |
| `ST` | `title-short` |
| `TI` | `title` |
| `VL` | `volume` |

`T2` and `SP` map to different CSL variables depending on the entry's reference type, so
they carry no single row above:

- `T2` is `collection-title` on `BOOK`, `CLSWK`, `COMP`, `EDBOOK`, `ELEC`, `MAP`, `MULTI`, `RPRT`, `UNPB` — types that are already their own container — and `container-title` everywhere else.
- `SP` is `number-of-pages` on `BOOK`, `EBOOK`, `EDBOOK`, `THES` — a whole work rather than something with a locator inside a container — and `page` everywhere else.

## Contributors

Contributor role is resolved from the tag and the entry's reference type together, since
no RIS specification fixes one tag to one role across every kind of entry:

| RIS tag | CSL role | Reference types |
| --- | --- | --- |
| `AU` | `editor` | `EDBOOK` |
| `AU` | `author` | everywhere else |
| `ED` | `editor` | all — Web of Science's own editor tag, used in place of `A2` |
| `A2` | `editor` | `ANCIENT`, `BLOG`, `CHAP`, `CONF`, `CPAPER`, `DICT`, `EBOOK`, `ECHAP`, `ENCYC`, `JOUR`, `MUSIC`, `SER` |
| `A2` | `collection-editor` | `BOOK`, `CLSWK`, `COMP`, `EDBOOK`, `ELEC`, `MAP`, `MULTI`, `RPRT`, `UNPB` |
| `A3` | `editor` | `BOOK` |
| `A3` | `collection-editor` | `ADVS`, `CHAP`, `CONF`, `EBOOK`, `MUSIC`, `SER`, `SLIDE`, `SOUND`, `VIDEO` |
| `A4` | `translator` | `ANCIENT`, `BOOK`, `CHAP`, `CLSWK`, `CTLG`, `DICT`, `EDBOOK`, `ENCYC`, `PAMP` |

A tag with no row for a given reference type is left unmapped there rather than guessed at.

## Dates

| RIS tag | CSL variable |
| --- | --- |
| `PY` | `issued` (anchor) |
| `DA` | refines `issued`'s precision, when its year agrees with `PY`'s |
| `Y1` | `issued`, only when `PY` is absent |
| `Y2` | `accessed` |

`PY` anchors the year; where `DA` also parses and agrees with it, `DA`'s extra precision
(month, or month and day) is kept. A `DA` whose year disagrees is left alone, and a `DA`
stating no year at all — Web of Science's own shape, `SEP 22` or `DEC` — is spliced onto
`PY`'s year instead, unless it is a month range, which is discarded rather than guessed at.
Without `PY`, `Y1` supplies the issued date at whatever precision it states. Where neither
resolves to a structured date but one carries text, that text is kept as a literal fallback
rather than discarded, `PY`'s own text taking precedence over `Y1`'s.

## Identifiers

| RIS tag | CSL key |
| --- | --- |
| `DO` | `DOI` |
| `UR` | `URL` |
| `SN` | `ISSN` or `ISBN`, resolved by the value's own shape |

`SN` is not disambiguated by the format itself. Its value is checked against the ISSN and
then the ISBN shape and stored under whichever matches, except on `PAT`, `RPRT`, where it is a report or patent number and not an identifier at all. `SN`'s three
producer encodings — Web of Science repeating the tag, Scopus annotating a value inline
and packing several behind `; `, EndNote continuing on an untagged line — are flattened
into one ordered list of individual values before this resolution runs. `DO` and `UR` take
the first value the entry carries, by source position; every other value of any of the
three tags is preserved on the item rather than discarded.

## Citation keys

RIS supplies no cite key of its own. `ID` is taken verbatim where the entry carries one;
otherwise a key is minted from the entry's own content — the first author's family name,
the issued year, and the title's first significant word (skipping `a`/`an`/`the`), lowercased
and run together with no separator. An entry missing any one of the three falls back to its
own position in the file instead, deterministically either way. What batch-scoped
de-duplication then stores may carry a suffix; the import result names the key as stored.

## A note on producer fixtures

Each producer's genuine test fixture carries a byte-for-byte fingerprint — a fragment only
that producer's export is known to contain — used solely to prove the vendored corpus is
what it claims to be. No mapping above depends on which producer wrote a file: there is no
producer-detection branch anywhere in this module, and every row applies uniformly regardless
of the file's origin.
