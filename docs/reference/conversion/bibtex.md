# BibTeX mapping

What this package makes of a `.bib` file: which entry type becomes which
CSL item type, and which field becomes which CSL variable. Both dialects are
listed together, each row saying which one it belongs to.

This page is generated from the mapping tables themselves, so it cannot
describe something the importer does not do. A field with no row here is not
discarded: it is kept with the record under `custom`, where it can be read
back afterwards.

## Entry types

| BibTeX entry type | CSL item type | Dialect |
| --- | --- | --- |
| `@article` | `article-journal` | classic |
| `@artwork` | `graphic` | biblatex |
| `@book` | `book` | classic |
| `@bookinbook` | `chapter` | biblatex |
| `@booklet` | `pamphlet` | classic |
| `@collection` | `collection` | biblatex |
| `@conference` | `paper-conference` | classic |
| `@dataset` | `dataset` | biblatex |
| `@electronic` | `webpage` | biblatex |
| `@inbook` | `chapter` | classic |
| `@incollection` | `chapter` | classic |
| `@inproceedings` | `paper-conference` | classic |
| `@inreference` | `entry` | biblatex |
| `@manual` | `book` | classic |
| `@mastersthesis` | `thesis` | classic |
| `@misc` | `document` | classic |
| `@mvbook` | `book` | biblatex |
| `@mvcollection` | `collection` | biblatex |
| `@mvproceedings` | `book` | biblatex |
| `@mvreference` | `book` | biblatex |
| `@online` | `webpage` | biblatex |
| `@patent` | `patent` | biblatex |
| `@periodical` | `periodical` | biblatex |
| `@phdthesis` | `thesis` | classic |
| `@proceedings` | `book` | classic |
| `@reference` | `book` | biblatex |
| `@report` | `report` | biblatex |
| `@suppbook` | `chapter` | biblatex |
| `@suppcollection` | `chapter` | biblatex |
| `@techreport` | `report` | classic |
| `@thesis` | `thesis` | biblatex |
| `@unpublished` | `manuscript` | classic |

An entry type with no row above becomes `document` rather than failing the entry.

## Fields

| BibTeX field | CSL variable | Dialect |
| --- | --- | --- |
| `abstract` | `abstract` | classic |
| `address` | `publisher-place` | classic |
| `annotation` | `annote` | biblatex |
| `annote` | `annote` | classic |
| `author` | `author` | classic |
| `booktitle` | `container-title` | classic |
| `chapter` | `chapter-number` | classic |
| `doi` | `DOI` | classic |
| `edition` | `edition` | classic |
| `editor` | `editor` | classic |
| `howpublished` | `medium` | classic |
| `institution` | `publisher` | classic |
| `isbn` | `ISBN` | classic |
| `issn` | `ISSN` | classic |
| `journal` | `container-title` | classic |
| `journaltitle` | `container-title` | biblatex |
| `keywords` | `keyword` | classic |
| `langid` | `language` | biblatex |
| `language` | `language` | classic |
| `location` | `publisher-place` | biblatex |
| `note` | `note` | classic |
| `number` | `issue` | classic |
| `organization` | `publisher` | classic |
| `pages` | `page` | classic |
| `pagetotal` | `number-of-pages` | biblatex |
| `publisher` | `publisher` | classic |
| `school` | `publisher` | classic |
| `series` | `collection-title` | classic |
| `shorttitle` | `title-short` | classic |
| `title` | `title` | classic |
| `type` | `genre` | classic |
| `url` | `URL` | classic |
| `volume` | `volume` | classic |

## Dates

| BibTeX field | CSL variable |
| --- | --- |
| `date` | `issued` |
| `year`, `month` | `issued` |
| `urldate` | `accessed` |

A BibLaTeX `date` takes precedence over a classic `year` and `month` pair, and
a date that will not resolve to a structured value is kept as written rather
than dropped.
