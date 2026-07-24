# Tasks: CSL JSON Data Model and Conversion

**Input**: Design documents from `/specs/001-csl-json-data-model/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/csl-json.md ✅, quickstart.md ✅

**Tests**: Included — explicitly required by FR-011 (all models/converters/date forms) and SC-003 (90%+ coverage).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `literature` Django app skeleton and test-runner infrastructure so that subsequent phases have somewhere to write code.

- [x] T001 Create `literature/` app skeleton: `literature/__init__.py`, `literature/apps.py` (AppConfig with `name = "literature"`, `label = "literature"`, `default_auto_field = "django.db.models.BigAutoField"`), `literature/migrations/__init__.py`
- [x] T002 Create test infrastructure: `tests/__init__.py`, `tests/settings.py` (minimal Django settings with `INSTALLED_APPS = ["ordered_model", "literature"]`, `DATABASES` SQLite in-memory, `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"`), `tests/conftest.py` with shared `@pytest.fixture` factories for `Item`, `Name`, `ItemDate`, and `ItemIdentifier` (using `pytest.mark.django_db` defaults) per Constitution Principle IV ("fixture factories MUST use pytest fixtures"); each factory must accept keyword overrides so tests can customise only what they need. **Database isolation**: all test functions and fixture factories that touch the database MUST use `@pytest.mark.django_db` with default rollback isolation (do NOT use `transaction=True` unless explicitly required for a specific test, and document why)

**Checkpoint**: `poetry run pytest` runs without collection errors (no tests yet).

- [x] T026 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [x] T027 ⚠️ CRITICAL: Run test collection: `poetry run pytest -v` — MUST pass with 0 errors (no tests yet; confirms no broken imports)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core lookup enums and date-parsing utilities that ALL models and conversion logic depend on. Must be complete before any user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 Create `literature/choices.py` with four `TextChoices` enums: `ItemType` (all **45** CSL item type values per authoritative schema at `tests/data/csl-data.json` — article, article-journal, article-magazine, article-newspaper, bill, book, broadcast, chapter, classic, collection, dataset, document, entry, entry-dictionary, entry-encyclopedia, event, figure, graphic, hearing, interview, legal_case, legislation, manuscript, map, motion_picture, musical_score, pamphlet, paper-conference, patent, performance, periodical, personal_communication, post, post-weblog, regulation, report, review, review-book, software, song, speech, standard, thesis, treaty, webpage). **Note**: 4 types use underscores in the CSL JSON 1.0.2 schema — not hyphens — and MUST be stored with underscores as their `.value` strings: `legal_case`, `motion_picture`, `musical_score`, `personal_communication`. Use these exact forms; do NOT normalise them to hyphens. `NameRole` (26 CSL name-variable roles per data-model.md), `DateType` (6 CSL date-variable slots: accessed, available-date, event-date, issued, original-date, submitted), `IdentifierType` (6 known types: DOI, ISBN, ISSN, PMID, PMCID, URL). Apply `gettext_lazy` i18n wrapping to all descriptive labels; exempt pure-acronym labels (DOI, ISBN, ISSN, PMID, PMCID, URL) per FR-018.
- [x] T004 [P] Create `literature/utils/__init__.py` (empty) and `literature/utils/date.py` with `parse_date_parts(date_parts: list) -> PartialDate | None` helper that converts a CSL `date-parts` single array (e.g. `[2019]`, `[2019, 8]`, `[2019, 8, 16]`) to a `partial_date.PartialDate` using `django-partial-date`; returns `None` on parse failure. Include module docstring mapping to CSL JSON `date-parts` spec.

**Checkpoint**: Foundation ready — `poetry run pytest` still passes (no broken imports).

- [x] T028 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [x] T029 ⚠️ CRITICAL: Run test collection: `poetry run pytest -v` — MUST pass with 0 errors (confirms choices + utils import cleanly)

---

## Phase 3: User Story 1 — Store and Retrieve Bibliographic Entries (Priority: P1) 🎯 MVP

**Goal**: A developer can create, persist, query, and relate all CSL JSON bibliographic data (items, names, dates, identifiers) using standard Django ORM patterns with zero data loss.

**Independent Test**: Create Item instances for multiple CSL types, add Name/ItemName links, add ItemDate (year-only, year-month, full date, date range), add ItemIdentifier records, save to DB, retrieve, and assert all fields unchanged.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 [P] [US1] Create `tests/test_models.py` with failing tests covering: (a) `Item` CRUD parametrized across **all 45 CSL item types** (one minimal fixture per type — just `citation_key` + `type`); (b) field-level persistence for all required + representative optional fields; (c) `Name` model stores all name parts including `literal`-only record; (d) `ItemName` through-model records role and preserves `order_with_respect_to=(item, role)` ordering; (e) `ItemDate` stores year-only, year-month, full date, date range with correct `begin`/`end`; (f) `ItemIdentifier` stores all 6 known identifier types and allows unknown string type; (g) model `__str__` methods return non-empty strings; (h) `UniqueConstraint` on `(item, date_type)` and `(item, type)` for identifiers is enforced
- [x] T006 [P] [US1] Create `tests/test_choices.py` with failing tests verifying: `ItemType` has exactly **45** values; `NameRole` has exactly 26 values; `DateType` has exactly 6 values; `IdentifierType` has exactly 6 values; 41 `ItemType` values use lowercase-hyphenated format and exactly 4 use lowercase-underscored format (`legal_case`, `motion_picture`, `musical_score`, `personal_communication`) — matching the authoritative CSL JSON 1.0.2 schema in `tests/data/csl-data.json` exactly; all 45 `ItemType` values are unique (no accidental duplicates); assert `ItemType` values against a reference set loaded from `tests/data/csl-data.json` (not a hardcoded list) to catch future schema drift

### Implementation for User Story 1

- [x] T007 [US1] Create `literature/models.py` with `Item` model: all 60+ scalar fields from data-model.md (citation_key, type, title, title_short, abstract, note, annote, publisher, publisher_place, all container/volume/issue/page/number fields, all event/archive/jurisdiction fields, keyword, categories JSONField, custom JSONField, citation_label, citation_number, journal_abbreviation, year_suffix, created, modified). Apply `gettext_lazy` to all `verbose_name`, `help_text`, `Meta.verbose_name/verbose_name_plural`. Include class docstring mapping to "CSL JSON top-level item object". Add `db_index=True` on `citation_key`, `type`, `title`, `container_title`, `publisher`. Implement `__str__` returning `citation_key`.
- [x] T008 [P] [US1] Add `Name` model to `literature/models.py`: all 10 fields from data-model.md (family, given, dropping_particle, non_dropping_particle, suffix, literal, comma_suffix, static_ordering, parse_names, created, modified). Add `Meta.indexes = [models.Index(fields=["family", "given"], name="name_family_given_idx")]` (do NOT use the deprecated `index_together` — removed in Django 5.x). Include model docstring and `gettext_lazy` i18n on all labels. Implement `__str__` returning `"{family}, {given}"` or `literal` when family/given are empty.
- [x] T009 [US1] Add `ItemName` model to `literature/models.py` (extends `ordered_model.models.OrderedModel`): FK to `Item` and `Name` (both CASCADE), `role` field (choices=`NameRole`, no default), `order_with_respect_to = ("item", "role")`, `UniqueConstraint` on `(item, role, name)` named `"unique_name_per_role_per_item"`. Include model docstring. Add `indexes` on `(item, role, order)` and `(name, role)`. Apply `gettext_lazy` to `Meta.verbose_name`, `Meta.verbose_name_plural`, and all field `help_text` values per FR-018.
- [x] T010 [P] [US1] Add `ItemDate` model to `literature/models.py`: FK to `Item` (CASCADE), `date_type` (choices=`DateType`), `begin` (PartialDateField, null/blank), `end` (PartialDateField, null/blank), `season` (CharField 20, blank), `circa` (BooleanField default=False), `literal` (CharField 255, blank), `raw` (CharField 255, blank), `raw_date_parts` (JSONField null/blank). Add `UniqueConstraint` on `(item, date_type)` named `"unique_date_type_per_item"`. Include model docstring and `gettext_lazy` i18n.
- [x] T011 [P] [US1] Add `ItemIdentifier` model to `literature/models.py`: FK to `Item` (CASCADE), `type` (CharField 50, required, **no `choices=` kwarg** — `IdentifierType` is used for documentation and lookup only; omitting `choices=` prevents Django's `full_clean()` from rejecting unknown identifier type strings, satisfying FR-017), `value` (CharField 500). Add `UniqueConstraint` on `(item, type)` named `"unique_identifier_type_per_item"`. Add `indexes` on `(item, type)`, `(type, value)`, `value`. Include model docstring and `gettext_lazy` i18n. **Design note**: the `(item, type)` uniqueness constraint means each item stores at most one identifier per type. Multiple ISBNs (ISBN-10 + ISBN-13) are out of scope for this feature; document this limitation in the `ItemIdentifier` model docstring.
- [x] T012 [US1] Generate `literature/migrations/0001_initial.py` by running `poetry run python manage.py makemigrations literature`. Verify migration is self-contained and applies cleanly on a fresh SQLite database via `poetry run python manage.py migrate`.

**Checkpoint**: `poetry run pytest tests/test_models.py tests/test_choices.py` passes — all US1 acceptance scenarios verified.

- [x] T030 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [x] T031 ⚠️ CRITICAL: Run US1 tests: `poetry run pytest tests/test_models.py tests/test_choices.py -v` — ALL tests MUST pass

---

## Phase 4: User Story 2 — Convert Between Model and CSL JSON (Priority: P2)

**Goal**: A developer can serialize any `Item` instance to a valid CSL JSON `dict` and deserialize a CSL JSON `dict` back to a new `Item` instance with full round-trip fidelity.

**Independent Test**: Create an `Item` with representative fields, names, dates (all 5 date forms), and identifiers; call `to_csl_json()`, then `from_csl_json()` on the result; assert every field on the round-tripped instance matches the original.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T013 [P] [US2] Create `tests/test_converters.py` with failing tests covering contract from `contracts/csl-json.md`:
  - `to_csl_json()`: output always has `"id"` = `citation_key` and `"type"`; blank fields are omitted; name arrays are ordered; known identifiers are top-level keys; unknown identifiers go to `custom`; real fixture from `tests/data/publication-csl.json`; **parametrize across all 45 `ItemType` values** (round-trip: create minimal item of each type, export, re-import, assert `type` field unchanged)
  - `from_csl_json()`: missing `type` raises `ValidationError`; unknown `type` raises `ValidationError`; missing both `citation-key` and `id` raises `ValidationError`; `citation-key` preferred over `id`; citation key suffix deduplication single-step (Smith2009 → Smith2009b); **deduplication wrap-around test**: pre-create items with suffixes `b` through `z` (25 items), then import with the same base key and assert the resolved key is `Smith2009aa`
  - Date round-trips: year-only (`[[2019]]`), year-month (`[[2019, 8]]`), full date (`[[2019, 8, 16]]`), full date range (`[[2019, 8, 12], [2019, 8, 16]]`), partial range with `raw_date_parts` fallback
  - Literal name round-trip (name object with only `"literal"` key)
  - `from_csl_json_list()`: successfully imports list, skips invalid items with warning, returns only valid items

### Implementation for User Story 2

- [x] T014 [US2] Create `literature/converters.py` with `to_csl_json(item: Item) -> dict`: map `citation_key` → `"id"` and `"type"`; iterate all scalar fields via Django `_meta` field introspection, converting snake_case field names to CSL JSON keys (hyphenated/camelCase); omit blank/null values; serialize `ItemName` records per role into ordered name arrays (only non-empty name parts); serialize `ItemDate` records using `begin`/`end` PartialDate → `date-parts` arrays (respecting partial-date precision), plus `raw_date_parts` fallback, `literal`, `season`, `circa`; serialize `ItemIdentifier` records (known types as top-level keys; unknown in `custom`); include `categories`/`custom` JSONField as-is. Add module and function docstrings per FR-010.
- [x] T015 [US2] Add `from_csl_json(data: dict) -> Item` to `literature/converters.py`: validate `type` present + in `ItemType` choices (raise `ValidationError` on failure); resolve `citation_key` from `citation-key` then `id` fallback (raise `ValidationError` if both absent); deduplicate citation key with letter suffix loop per FR-005 deduplication rules (b→c→…→z→aa→ab…); map CSL JSON field names to Django field names and create `Item`; create `Name`/`ItemName` records for each name-variable key — find-or-create `Name` using `(family, given, literal, dropping_particle, non_dropping_particle, suffix)` as the composite lookup key (all blank/None fields included in the equality check; if no matching `Name` exists, create a new one); respect `literal`-only names per FR-016; create `ItemDate` records using `parse_date_parts()` utility for `begin`/`end`; store `raw_date_parts` fallback when parse fails; create `ItemIdentifier` records for DOI/ISBN/ISSN/PMID/PMCID/URL top-level keys plus unknown identifier-like keys from `custom` using `logger.warning()` per FR-017; call `full_clean()` on **every** model instance (`Item`, `Name`, `ItemDate`, and `ItemIdentifier`) before saving to enforce all model-layer validators (Constitution Principle III — data integrity); use eager `gettext` for all validation error messages per FR-018. Add docstring per FR-010.
- [x] T016 [US2] Add `from_csl_json_list(data: list[dict]) -> list[Item]` to `literature/converters.py`: iterate items, call `from_csl_json()` for each, catch `ValidationError` per item and emit `logger.warning()`, return list of successfully created instances. Add docstring.

**Checkpoint**: `poetry run pytest tests/test_converters.py` passes — all US2 acceptance scenarios and round-trip invariants verified.

- [x] T032 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [x] T033 ⚠️ CRITICAL: Run US2 tests: `poetry run pytest tests/test_converters.py -v` — ALL tests MUST pass

---

## Phase 4b: FR-020 — Identifier Value Validation (Constitution I gate)

**Purpose**: Model-layer format validators on `ItemIdentifier.value` for all well-known identifier types. Required by Constitution Principle I ("invalid identifiers MUST NOT be silently stored") and FR-020.

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [x] T024 [P] Create `tests/test_validators.py` with failing tests covering FR-020/SC-006: (a) valid DOI, ISBN-10, ISBN-13, ISSN, URL, PMID, PMCID values are accepted; (b) malformed DOI (no `10.` prefix), invalid ISBN (wrong check digit), malformed ISSN, relative URL, non-numeric PMID all raise `ValidationError`; (c) unknown identifier type with any value string is accepted without error
- [x] T025 Create `literature/validators.py` with validators: `validate_doi` (regex `^10\.\d{4,}/\S+$`), `validate_isbn` (digits-only strip then ISBN10/ISBN13 check-digit verification), `validate_issn` (regex `^\d{4}-\d{3}[\dX]$`), `validate_url` (reuse `django.core.validators.URLValidator` with `schemes=["http","https","ftp"]`), `validate_pmid` (numeric string), `validate_pmcid` (numeric string). All error messages use `gettext_lazy` per FR-018. Update `ItemIdentifier` model (T011/T007 in models.py) to attach the correct validator by type in a `clean()` method that looks up the type and calls the matching validator, raising `ValidationError` on failure.

- [x] T034 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [x] T035 ⚠️ CRITICAL: Run validator tests: `poetry run pytest tests/test_validators.py -v` — ALL tests MUST pass

---

## Phase 5: User Story 3 — Understand the Models via Documentation (Priority: P3)

**Goal**: Every public model class, field, and conversion function has a docstring that identifies its CSL JSON mapping and purpose, satisfying SC-004 (0 undocumented public interfaces).

**Independent Test**: Programmatically inspect all public classes, fields, and functions in `literature.models`, `literature.converters`, `literature.utils.date`, and `literature.choices` and assert `__doc__` is non-empty. Verify `help_text` is set on all `Item` model fields that correspond to CSL JSON fields.

### Implementation for User Story 3

- [x] T017 [P] [US3] Audit and complete docstrings in `literature/models.py`: ensure every model class docstring states CSL JSON mapping and purpose; ensure every field that maps to a CSL JSON field has `help_text` identifying the CSL JSON field name (e.g., `help_text=_("CSL JSON: container-title")`); add `__str__` docstrings for all models.
- [x] T018 [P] [US3] Audit and complete docstrings in `literature/converters.py`: ensure `to_csl_json` docstring describes input (`Item` instance), output (CSL JSON dict), guarantees (always has `id`, `type`; omits blank fields), and representation changes (number → string); ensure `from_csl_json` docstring describes validation preconditions, citation key deduplication logic, and all edge cases from contracts/csl-json.md; ensure `from_csl_json_list` docstring describes batch behavior and skip-on-error semantics.
- [x] T019 [P] [US3] Audit and complete docstrings in `literature/utils/date.py` and `literature/choices.py`: ensure module-level and class-level docstrings explain CSL JSON mapping; verify all `NameRole`, `DateType`, `IdentifierType`, and `ItemType` entries have descriptive labels wrapped with `gettext_lazy` where applicable (per FR-018 exemptions for pure acronyms).
- [x] T038 [P] [US3] Create `tests/test_documentation.py` with parametrized tests that use `inspect` to iterate all public symbols (non-underscore names) in `literature.models`, `literature.converters`, `literature.choices`, and `literature.utils.date`, asserting `__doc__` is non-empty for each class and each public function/method. Also parametrize across all `Item` fields and assert `help_text` is non-empty for every field that corresponds to a CSL JSON key. This mechanically enforces SC-004 ("0 undocumented public interfaces") without relying solely on manual audit.

**Checkpoint**: `poetry run pytest` still passes; T038 programmatically confirms SC-004 is satisfied (0 undocumented public interfaces).

- [x] T036 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [x] T037 ⚠️ CRITICAL: Run full test suite: `poetry run pytest -v` — ALL tests MUST pass before starting Phase 6

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: i18n catalog, coverage gate, linting, demo app validation, and quickstart validation.

- [x] T020 Create `literature/locale/en/LC_MESSAGES/` directory structure and run `poetry run django-admin makemessages -l en --ignore=.venv` from the `literature/` directory to generate `literature/locale/en/LC_MESSAGES/django.po`. Verify command exits 0 (no errors). Commit `.po` file. This satisfies FR-019 and SC-005.
- [x] T021 [P] Run `poetry run pytest --cov=literature --cov-report=term-missing` and verify line coverage is ≥ 90% across `literature/models.py`, `literature/converters.py`, `literature/choices.py`, `literature/utils/date.py`. Fix any coverage gaps (SC-003).
- [x] T022 [P] Run `poetry run ruff check literature tests` and resolve all lint warnings. Verify all `gettext`/`gettext_lazy` import patterns are correct per FR-018 (module-level strings use `gettext_lazy`; function-body strings use eager `gettext`).
- [x] T039 [P] Run `poetry run mypy literature` and verify exit code 0 (0 errors). Constitution Principle IV requires type annotations on all core package code. Ensure all public function signatures in `literature/converters.py`, `literature/utils/date.py`, and `literature/validators.py` have annotated parameters and return types. mypy is already configured in `pyproject.toml` with `mypy_django_plugin.main` — the gate MUST pass before merge.
- [x] T023 Verify the demo app (Constitution Principle VI): run `poetry run python manage.py migrate --run-syncdb` on a clean database, then `poetry run python manage.py check --deploy` (ignoring deployment-only warnings). Confirm at least one `Item` with a full name, date, and identifier can be created and round-tripped via `from_csl_json` / `to_csl_json` from the shell. Document any import errors as bugs to fix before merge, demo app migrates and round-trips cleanly.
- [x] T040 Write user-facing project documentation: (a) fill in `README.md` with project description, feature list, requirements, installation steps, quick-start code examples, and a data model overview table; (b) create `docs/conf.py` (Sphinx config using myst-parser, sphinx.ext.autodoc, sphinx_design, sphinx_copybutton, alabaster theme, Django setup for autodoc); (c) create `docs/index.md` (toctree root); (d) create `docs/installation.md` (requirements, pip install, INSTALLED_APPS, migrate, i18n note); (e) create `docs/data-model.md` (entity diagram, per-model field table with CSL JSON mapping, design notes); (f) create `docs/usage.md` (manual creation, import, export, queries, round-trip); (g) create `docs/api/` with auto-generated stubs for `literature.models`, `literature.converters`, `literature.choices`, `literature.validators`, `literature.utils.date`. Verify `poetry run sphinx-build -b html docs docs/_build/html` exits 0.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)          ← No dependencies
Phase 2 (Foundational)   ← Depends on Phase 1
Phase 3 (US1 - Models)   ← Depends on Phase 2  [BLOCKS Phase 4]
Phase 4 (US2 - Convert)  ← Depends on Phase 3
Phase 4b (Validators)    ← Depends on Phase 3 (ItemIdentifier model exists); can run alongside Phase 4
Phase 5 (US3 - Docs)     ← Can start after Phase 3 (models exist); finalized after Phase 4/4b
Phase 6 (Polish)         ← Depends on Phases 3, 4, 4b, 5
```

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Phase 2 Foundational. No dependency on other stories.
- **User Story 2 (P2)**: Must follow US1 (requires models to exist for conversion).
- **User Story 3 (P3)**: Starts after US1 models are created; finalized after US2 converters are written.
- **FR-020 Validators (Phase 4b)**: Can run in parallel with Phase 4; depends only on `ItemIdentifier` model from Phase 3.

### Phase Gate Tasks (non-negotiable blockers)

Every phase ends with two gate tasks that MUST pass before the next phase begins:

1. `poetry run python manage.py check` — Django system checks (catches misconfigured models, missing migrations, etc.)
2. `poetry run pytest <phase-relevant-tests> -v` — full green test run for all tests written so far

| Phase gate | System check | pytest command |
|---|---|---|
| After Phase 1 | T026 | T027 (`poetry run pytest -v`) |
| After Phase 2 | T028 | T029 (`poetry run pytest -v`) |
| After Phase 3 | T030 | T031 (`tests/test_models.py tests/test_choices.py`) |
| After Phase 4 | T032 | T033 (`tests/test_converters.py`) |
| After Phase 4b | T034 | T035 (`tests/test_validators.py`) |
| After Phase 5 | T036 | T037 (`poetry run pytest -v` — full suite, includes T038 docs tests) |
| Phase 6 quality gates | — | T039 (`poetry run mypy literature`), T021 (coverage ≥ 90%), T022 (ruff) |

### Within Each User Story

- Test tasks (`T005`, `T006`) must be written FIRST and FAIL before implementation
- `Item` model (T007) before `ItemName` (T009) — `ItemName` has FK to `Item`
- All models (T007–T011) before migration generation (T012)
- Converter tests (T013) before converter implementation (T014–T016)

### Parallel Opportunities

**Phase 2**: T003 and T004 can run in parallel (different files)

**Phase 3 (US1) tests**: T005 and T006 can run in parallel (different files)

**Phase 3 (US1) implementation**: T008 (`Name`), T010 (`ItemDate`), T011 (`ItemIdentifier`) can run in parallel after T007 (`Item`) is complete

**Phase 4b (Validators)**: T024 and T025 can run in parallel with Phase 4 tasks T013–T016 since they touch different files (`validators.py`, `test_validators.py`)

**Phase 5 (US3)**: T017, T018, T019, T038 can all run in parallel (different files)

**Phase 6**: T021, T022, and T039 can run in parallel

---

## Parallel Example: User Story 1

```text
# Step 1 (parallel): Write failing tests
T005: tests/test_models.py
T006: tests/test_choices.py

# Step 2: Item model (must come first)
T007: literature/models.py → Item

# Step 3 (parallel after T007):
T008: literature/models.py → Name
T010: literature/models.py → ItemDate
T011: literature/models.py → ItemIdentifier

# Step 4 (after T008): ItemName through-model
T009: literature/models.py → ItemName

# Step 5 (after T007-T011): Generate migration
T012: literature/migrations/0001_initial.py
```

---

## Implementation Strategy

**MVP Scope**: Complete **Phase 1 + Phase 2 + Phase 3** for a functional, queryable bibliographic database (User Story 1). This alone satisfies the foundational requirement and makes Phase 4 work unblocked.

**Incremental delivery order**:

1. Phase 1 → Phase 2 → Phase 3 (US1) = Working models with tests
2. Phase 4 (US2) = Working conversion with round-trip tests
3. Phase 5 (US3) = Documentation completeness
4. Phase 6 = Polish (coverage gate, i18n catalog, lint)

**Key design risks to watch**:

- `ItemName` `order_with_respect_to = ("item", "role")` — verify `django-ordered-model` 3.7+ supports tuple ordering (see research.md)
- `PartialDate` precision encoding in `date-parts` arrays — `parse_date_parts()` must correctly map between `partial_date.PartialDate.precision` and array length
- Citation key deduplication loop in `from_csl_json()` — must handle the full `a`→`z`→`aa`→`ab` sequence correctly (per FR-005; T013 wrap-around test verifies this path)
- `ItemType` choices — all 45 values must match CSL JSON 1.0.2 schema exactly; validate against `tests/data/csl-data.json`
- `ItemIdentifier` validators (FR-020) — ISBN check-digit logic is non-trivial; consider using a third-party library (`isbnlib`) or implement from scratch with a dedicated unit test
