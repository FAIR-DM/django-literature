# Documentation standards

These rules cover the documentation a person reads to use what this repository makes: the pages
under `docs/` and the quickstart in the README. `CONSTITUTION.md` makes them binding. Docstrings,
component annotations and comments are covered by
[`code-documentation.md`](code-documentation.md). The sections above **Project additions** are
shared unchanged with our other repositories. They set the defaults. A repository changes a
default, or adds to it, in **Project additions** only.

The site is laid out the way Django packages are usually documented: a homepage that gets the
reader installed, guides organised by feature, and a reference. What each passage does follows
[Diátaxis](https://diataxis.fr/), which sorts writing by what the reader needs at the moment they
read it. Diátaxis decides how a passage is written, not where the page goes.

## 1. What these rules cover

They cover documentation written for the people who use the repository's work:

- for a package, the developer who installs it in their own project,
- for an application, the person who uses the site.

Material written for the people who maintain the repository is covered by section 8 only:

- the changelog,
- decision records in `docs/adr/`,
- the roadmap,
- specifications in `specs/`,
- the contributing pages and standards in `docs/contributing/`,
- files that configure tools.

## 2. When a package needs a `docs/` directory

**A small package needs none.** When setting the package up takes no more than two short
examples, the README is its documentation. A package that needs more has a `docs/` directory laid
out as below, and the README's quickstart links to it.

## 3. The site

### Navbar

The navbar holds, in order:

1. **Home**, the homepage, written first in its contents as `Home <self>`.
2. **Tutorial**, only when the repository has one.
3. **The guides**, one entry for each (section 4).
4. **Reference** (section 6).
5. **Contributing** (section 8).
6. **Changelog**, a link to `CHANGELOG.md` in the repository.

A repository may add an entry, such as a Topics section (section 7), and says so in
**Project additions**.

### Where pages live

```text
docs/
├── index.md
├── tutorial.md            only when there is one
├── developer/             one directory for each guide (section 4)
├── reference/
├── contributing/
└── adr/
```

- **Each section has its own `index.md`**, titled with the section's name, which says in one
  sentence who it is for and what its pages cover, and lists them.
- **A directory is created when its first page arrives.** None is set up in advance or left
  empty.
- **A file is named after its title**, in lowercase words joined by hyphens:
  `developer/importing.md`, `reference/settings.md`.
- **Related pages share a subdirectory** with its own `index.md`, and their titles drop what the
  subdirectory already says: `reference/format-mapping/bibtex.md` is titled "BibTeX".
- **A tutorial longer than one page** becomes a `tutorial/` directory, its pages numbered in the
  order they are read.

### The homepage

`index.md` is the page most readers start and finish on. It carries, in this order:

1. **The project's name** as a reader writes it, "Django Literature", never the distribution name.
2. **A summary** of what it is for, in one paragraph.
3. **Its features**, as a list, each linking to the guide page for that feature.
4. **Requirements**: the supported Python and Django versions, and what each optional extra needs.
5. **Installation**: every step to a working install of the core, such as `pip install`,
   `INSTALLED_APPS` and `migrate`, ending with links to the full installation pages.
6. **An example**: a short, complete piece of code and what it gives.
7. **Next steps**: one line for each guide and for the reference.
8. **About the project**: links to `GOALS.md`, `CONTEXT.md` (as "Domain model"),
   `CONSTITUTION.md` and the changelog, one line each on what it holds.
9. **Support**: where to report a problem, and the code of conduct.
10. **Licence.**

### The changelog

The changelog is linked from the navbar and the homepage, and never copied or included into the
site. Its links are written for the repository, and a copy drifts.

## 4. Guides

A guide is written for one reader doing one kind of work. **A repository has one guide unless it
declares more:**

- **a package**: the Developer guide, in `docs/developer/`, for the developer building with it,
- **an application**: the User guide, in `docs/user/`, for the person using the site.

A repository whose parts are used by different readers declares its guides in
**Project additions** with a table headed **Guides**:

```markdown
### Guides

| Guide | Lives in | Reader | Covers |
|---|---|---|---|
| Developer guide | `developer/` | A developer building with the package from Python | Installing the core, storing, importing and exporting references |
| Web interface | `ui/` | A developer adding the pages, and the people using them | Installing the pages, each page, using them in your own project |
```

- **Guides are told apart by what the reader does**, not by what they are allowed to do. A role
  that only sees one more button gets a line on the page for that feature.
- **A guide is named for what its reader uses**, such as "Web interface", not for the technology.
- **Each guide's `index.md` says who it is for** and links to the guides beside it.
- **An optional part gets its own guide** when it is installed separately and has pages of its
  own, such as a package's web interface. Its installation page is the first page of that guide.

### Guide pages

- **One page for each feature**, titled with the feature's name: "Importing", "The catalogue".
- **The page opens** with what the feature does, in a paragraph with no heading.
- **Its tasks are sections**, each titled with a verb and what it acts on: "Import a BibTeX file",
  never "How to import a BibTeX file". A task's steps follow section 5.
- **Explanation of the feature closes the page**, in sections titled with what they explain:
  "Why citation keys may repeat" (section 7).
- **The sidebar groups pages under captions**, with Getting started first, holding installation
  and upgrading.
- **An application's user guide follows the application's own sections**, because a person looks
  for help under the name of the screen they are on. Its reference is a screen guide (section 6).

### Installation

The core's installation appears twice: briefly on the homepage, and in full as the first page of
the first guide, saying what each step sets up. An optional part is installed on the first page of
its own guide.

## 5. Tutorials and tasks

A **tutorial** takes someone new from nothing to a working result.

- **Title**: what the reader will have built, such as "Build your first page".
- **Before you start**: what the reader needs, with a link for each.
- **One path.** No options, no alternatives and no "you could also".
- **Every step ends with something the reader can see**: a page that loads, a command's output,
  a test that passes.
- **The code is complete.** Each block can be copied as it stands, with its imports. A name the
  reader must change, such as `yourproject`, is called out the first time it appears.
- **It explains almost nothing.** One sentence at most, then a link.
- **It ends with the finished result**, and links to the guide pages a reader is likely to want
  next.

A tutorial is followed from start to finish, in a new project, before a release that changes
anything it relies on.

A **task**, a section of a guide page, takes someone who already uses the package through one job.

- **Opening sentence**: what the task achieves and when someone would do it.
- **Steps**: one numbered list, one action to a step. Code in a step shows only what that step
  changes, with enough around it to show where it goes. A task of one step needs no list.
- **The result**: what the reader sees once it is done, and anything that changed elsewhere.
- Every setting, component or command it uses links to its reference entry.

**Troubleshooting is a set of tasks.** Each is headed by the symptom the reader sees, gives the
cause in one sentence, then the fix.

## 6. Reference

The reference describes the machinery: settings, models, template tags, management commands, file
formats and the Python API.

- **It describes, and does nothing else.** No steps and no argument. A short example is fine
  where it shows the usage faster than the prose can.
- **It is built like the thing it describes.** One page for the settings, one for the template
  tags, each in the order the code defines them or in alphabetical order.
- **Every entry gives the same facts in the same order**: the name, its type or signature, its
  default, what it does, and what it accepts.
- **It is complete.** Every public setting, component, tag and command has an entry. One that is
  missing is a defect.

**The Python API is generated from docstrings** wherever the repository builds its
documentation, and [`code-documentation.md`](code-documentation.md) makes those docstrings
complete. A docstring is never restated by hand. A repository without a docs build writes
reference pages only for what a user sets or calls from outside Python.

**A page a person uses is described in the guide for it**, not in the reference: a form, an import
page, a screen. In an application this is the screen guide, one page for each screen, titled
with the screen's own heading. It says what the screen is for and how to reach it, has one
section for each part of the screen saying what it shows and what it shows when empty, and closes
with what the reader can do from it, each action a link to its task.

## 7. Explanation

Explanation helps a reader understand why something works the way it does.

- **It sits on the guide page for the feature it explains**, as closing sections titled with what
  they explain, such as "What survives a round trip".
- **A Topics section is used only for explanation that covers several features at once**, such as
  how theming works across a whole component library. It sits in the navbar after the guides, and
  the repository declares it in **Project additions**.
- **Body**: one idea to a section. Why the design is the way it is, what it was weighed against,
  and where its limits are.
- **Decisions link to their record.** Where a decision has an entry in `docs/adr/`, the
  explanation gives the reasoning in a form a user can follow and links to the record.

Explanation never takes the reader through a task and never lists settings.

## 8. Contributing

`docs/contributing/` holds the maintainers' material. Its `index.md` opens with the code of
conduct and where to report a problem with someone's conduct. Its pages, in order:

1. **Set up a development environment**: what to install, cloning the repository, installing its
   dependencies and hooks, and running its demo or example project where it has one.
2. **Run the tests and checks**: the test suite, the linters and hooks, and building the
   documentation, each exactly as CI runs it.
3. **The standards**, under `standards/`.
4. **Decision records**, the roadmap, and anything else for maintainers, such as translating.

The commands on the first two pages come from the repository's own tooling, and each is run
before it is written down.

## 9. Every page

- **It reads on its own.** A reader arrives from search or from a link, so the opening says what
  the page covers.
- **It speaks to the reader as "you".**
- **It links rather than repeats.** A setting is described once, on its reference page, and
  linked from everywhere else. The README links to the documentation for anything past its
  quickstart.
- **It describes the current release.** What changed, and when, is in the changelog. A page has
  no "new in" notes and no record of how it used to work.

## 10. Enforcement

- Where the repository builds its documentation, the build treats warnings as errors, so a page
  left out of the contents or a broken cross-reference fails it.
- A conformance check flags a page outside the layout in section 3, or outside a declared guide.
- Everything else, including the homepage's contents and what each passage does, is checked in
  review.

## Project additions

### Guides

| Guide | Lives in | Reader | Covers |
|---|---|---|---|
| Developer guide | `developer/` | A developer building with the package from Python | Installing and upgrading the core, storing, importing and exporting references |
| Web interface | `ui/` | A developer installing and configuring the web interface, and the people using it | Installing the web interface, the catalogue, the add and edit form, importing a file, the reference picker, displaying references |

---

**Version**: 2.0.0
