"""Tests for the templates ``literature.ui`` ships."""

import re
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "literature" / "ui" / "templates" / "literature" / "ui"
TEMPLATE_PATHS = sorted(TEMPLATES_DIR.glob("*.html"))

# django-mvp's own packaged chain (research R2, plan.md D-1) — the app must
# never reach any of these, since a host that has not written its own
# base.html would get TemplateDoesNotExist through the packaged chain, and a
# top-level base.html of our own would hijack the host's shell.
FORBIDDEN_REFERENCES = ["page_view.html", "list_view.html", "detail_view.html"]


class TestBaseTemplate:
    """``literature/ui/templates/literature/ui/base.html`` — plan.md D-1."""

    @staticmethod
    def _source() -> str:
        return (TEMPLATES_DIR / "base.html").read_text()

    def test_extends_mvp_base_directly(self):
        assert '{% extends "mvp/base.html" %}' in self._source()

    def test_references_none_of_the_packaged_view_chain(self):
        source = self._source()
        for forbidden in FORBIDDEN_REFERENCES:
            assert forbidden not in source

    def test_does_not_extend_or_include_the_unqualified_base_template(self):
        source = self._source()
        assert '"base.html"' not in source
        assert "'base.html'" not in source

    def test_renders_the_page_wrapper_class(self):
        assert '<c-page class="{{ page.class }}">' in self._source()

    def test_renders_the_breadcrumbs_region(self):
        assert "<c-breadcrumbs" in self._source()


# ---------------------------------------------------------------------------
# T021 — utility-class allowlist. FR-008, D-7.
#
# django-mvp's own ``docs/utility-classes.md`` is the source of truth, but it
# ships only in the django-mvp *source repo*, not inside the installed
# package: ``pathlib.Path(mvp.__path__[0]).rglob('*utility*')`` returns
# nothing for django-mvp 0.17.0, so this test module cannot read it at test
# time. The allowlist below is that document's content, reproduced as data,
# read at django-mvp 0.17.0. Re-check it by hand against
# ``docs/utility-classes.md`` whenever django-mvp is bumped past 0.17.0.
#
# django-accounts-center shipping two workaround CSS rules is the evidence
# this mechanical check earns its keep: a class token outside the documented
# set can render correctly in dev against whatever stylesheet happens to be
# on disk and then break for a host that only ships the packaged one.
# ---------------------------------------------------------------------------

_SCALE = ["0", "1", "2", "3", "4", "5", "6", "8", "10", "12"]


def _expand(pattern: str) -> list[str]:
    """Expand one ``{a,b,c}`` or ``{1..12}`` (or both) group in a
    utility-classes.md pattern like ``items-{start,center,end}`` or
    ``rounded-{t,r,b,l}-{sm,md,lg,xl,full}``. A pattern with no ``{...}``
    group is already a literal class name and is returned unchanged."""
    match = re.search(r"\{([^{}]+)\}", pattern)
    if not match:
        return [pattern]
    options: list[str] = []
    for part in match.group(1).split(","):
        part = part.strip()
        if ".." in part:
            low, high = part.split("..")
            options.extend(str(n) for n in range(int(low), int(high) + 1))
        else:
            options.append(part)
    expanded: list[str] = []
    for option in options:
        expanded.extend(_expand(pattern[: match.start()] + option + pattern[match.end() :]))
    return expanded


def _expand_all(patterns: list[str]) -> set[str]:
    tokens: set[str] = set()
    for pattern in patterns:
        tokens.update(_expand(pattern))
    return tokens


def _scaled(prefixes: list[str], scale: list[str]) -> set[str]:
    return {f"{prefix}-{n}" for prefix in prefixes for n in scale}


# utility-classes.md's "responsive groups": bare, or behind md:/lg:/xl:.
_RESPONSIVE_GROUP_PATTERNS = [
    "block",
    "inline-block",
    "inline",
    "flex",
    "inline-flex",
    "grid",
    "hidden",
    "flex-row",
    "flex-col",
    "flex-wrap",
    "flex-nowrap",
    "flex-1",
    "flex-auto",
    "flex-none",
    "grow",
    "grow-0",
    "shrink",
    "shrink-0",
    "items-{start,center,end,baseline,stretch}",
    "justify-{start,center,end,between,around,evenly}",
    "content-{start,center,end,between,around,evenly}",
    "self-{auto,start,center,end,stretch}",
    "grid-cols-{1..12}",
    "col-span-{1..12,full}",
    "w-{auto,full,screen,min,max,fit,1/2,1/3,2/3,1/4,3/4}",
    "h-{auto,full,screen,min,max,fit}",
    "max-w-{xs,sm,md,lg,xl,2xl,3xl,4xl,5xl,6xl,7xl,full,none,prose}",
    "min-w-{0,full}",
    "max-h-{full,screen}",
    "min-h-{0,full,screen}",
    "text-{left,center,right,justify}",
    "text-{xs,sm,base,lg,xl,2xl,3xl,4xl,5xl,6xl}",
    "static",
    "relative",
    "absolute",
    "fixed",
    "sticky",
    "inset-0",
    "inset-x-0",
    "inset-y-0",
    "top-{0,auto}",
    "right-{0,auto}",
    "bottom-{0,auto}",
    "left-{0,auto}",
    "overflow-{auto,hidden,visible,scroll}",
    "overflow-x-auto",
    "overflow-y-auto",
]

RESPONSIVE_ALLOWED = (
    _expand_all(_RESPONSIVE_GROUP_PATTERNS)
    | _scaled(["gap", "gap-x", "gap-y"], _SCALE)
    | _scaled(["p", "px", "py", "pt", "pr", "pb", "pl"], _SCALE)
    | _scaled(["m", "mx", "my", "mt", "mr", "mb", "ml"], _SCALE)
    | {"m-auto", "mx-auto", "my-auto"}
)

# utility-classes.md's "base-only groups": never behind a responsive prefix.
_BASE_ONLY_PATTERNS = [
    "z-{0,10,20,30,40,50,auto}",
    "border",
    "border-0",
    "border-2",
    "border-4",
    "border-8",
    "border-t",
    "border-r",
    "border-b",
    "border-l",
    "rounded-{none,sm,md,lg,xl,2xl,3xl,full}",
    "rounded-{t,r,b,l}-{sm,md,lg,xl,full}",
    "opacity-{0,25,50,75,100}",
    "font-{sans,serif,mono}",
    "font-{light,normal,medium,semibold,bold,extrabold}",
    "leading-{none,tight,snug,normal,relaxed,loose}",
    "tracking-{tight,normal,wide}",
    "truncate",
    "whitespace-nowrap",
    "break-words",
    "italic",
    "uppercase",
    "lowercase",
    "capitalize",
    "underline",
    "no-underline",
    "cursor-{pointer,not-allowed,default}",
    "transition",
    "select-none",
    "pointer-events-none",
    "align-middle",
    "duration-{150,200,300}",
    "object-{cover,contain,fill}",
    "list-{none,disc,decimal}",
]

BASE_ONLY_ALLOWED = _expand_all(_BASE_ONLY_PATTERNS)

# utility-classes.md's colour utilities: bg-/text-/border- over the daisyUI
# semantic palette, base only — plus hover:/focus-visible: state variants.
_PALETTE = [
    "primary",
    "secondary",
    "accent",
    "neutral",
    "info",
    "success",
    "warning",
    "error",
    "primary-content",
    "secondary-content",
    "accent-content",
    "neutral-content",
    "info-content",
    "success-content",
    "warning-content",
    "error-content",
    "base-100",
    "base-200",
    "base-300",
    "base-content",
]

COLOUR_ALLOWED = {f"{prefix}-{colour}" for prefix in ("bg", "text", "border") for colour in _PALETTE}
STATE_ALLOWED = COLOUR_ALLOWED | {"opacity-75", "opacity-100", "underline"}

_RESPONSIVE_PREFIXES = ("md:", "lg:", "xl:")
_STATE_PREFIXES = ("hover:", "focus-visible:")
_REJECTED_PREFIXES = ("sm:", "2xl:")

_CLASS_ATTR_RE = re.compile(r'(?<!:)\bclass="([^"]*)"')
_TEMPLATE_EXPR_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)


def extract_class_tokens(source: str) -> list[str]:
    """Every whitespace-separated token inside a literal ``class="..."``
    attribute in ``source``. Cotton's bound ``:class="..."`` attributes are
    excluded by the negative lookbehind (a dynamic expression, not a literal
    class list) and so is every other Cotton component parameter
    (``size="sm"``, ``cols="1"``, ``gap="4"``) — none of those match
    ``class="``, only the attribute actually named ``class`` does. Any
    ``{{ ... }}`` or ``{% ... %}`` template expression inside the attribute
    value is stripped before splitting on whitespace, not filtered token by
    token after: a naive per-token filter lets a multi-word expression like
    ``{{ page.class }}`` leak its middle word (``page.class``) and closing
    delimiter (``}}``) through as if they were literal class names, which is
    exactly what ``literature/ui/templates/literature/ui/base.html``'s
    ``class="{{ page.class }}"`` would do if this stripped only the token
    that happened to contain the opening delimiter."""
    tokens: list[str] = []
    for match in _CLASS_ATTR_RE.finditer(source):
        value = _TEMPLATE_EXPR_RE.sub(" ", match.group(1))
        tokens.extend(value.split())
    return tokens


def is_allowed_utility_class(token: str) -> bool:
    """Is ``token`` a class django-mvp's utility-classes.md documents (bare,
    or behind the responsive/state prefix the document allows for its
    group)? Arbitrary values (``w-[37px]``) and opacity modifiers
    (``text-base-content/60``) are never in the reference document, so they
    fail by absence rather than by a special-cased rejection. The ``sm:``
    and ``2xl:`` prefixes are explicitly outside
    ``responsive_prefixes_allowed`` and are rejected outright, so a valid
    base name behind a disallowed prefix cannot slip through by accident."""
    if "{{" in token or "{%" in token:
        return False
    if token.startswith(_REJECTED_PREFIXES):
        return False
    for prefix in _STATE_PREFIXES:
        if token.startswith(prefix):
            return token[len(prefix) :] in STATE_ALLOWED
    for prefix in _RESPONSIVE_PREFIXES:
        if token.startswith(prefix):
            return token[len(prefix) :] in RESPONSIVE_ALLOWED
    return token in RESPONSIVE_ALLOWED or token in BASE_ONLY_ALLOWED or token in COLOUR_ALLOWED


class TestUtilityClassAllowlist:
    """T021 — FR-008, D-7. Every ``class`` token in a template
    ``literature.ui`` ships is a utility named in django-mvp's
    ``utility-classes.md`` (see the module-level allowlist above), behind
    only the prefix that document allows for its group. No daisyUI
    component class appears as a literal ``class="..."`` token in any
    shipped template today — the Cotton components (``<c-badge>``,
    ``<c-card>``, ...) supply their own daisyUI classes internally, so this
    allowlist does not need to enumerate daisyUI's component set to cover
    what is actually shipped."""

    @pytest.mark.parametrize("template_path", TEMPLATE_PATHS, ids=lambda p: p.name)
    def test_every_class_token_is_allowlisted(self, template_path):
        tokens = extract_class_tokens(template_path.read_text())
        disallowed = [token for token in tokens if not is_allowed_utility_class(token)]
        assert not disallowed, f"{template_path.name}: non-allowlisted class token(s) {disallowed}"

    @pytest.mark.parametrize(
        "token",
        ["w-[37px]", "text-base-content/60", "sm:flex", "2xl:hidden", "sm:hidden", "2xl:block"],
    )
    def test_rejects_arbitrary_values_opacity_modifiers_and_disallowed_prefixes(self, token):
        assert not is_allowed_utility_class(token)

    @pytest.mark.parametrize(
        "token",
        [
            "flex",
            "py-4",
            "text-lg",
            "font-semibold",
            "md:flex",
            "lg:grid-cols-6",
            "xl:hidden",
            "text-primary",
            "hover:text-primary",
            "focus-visible:opacity-75",
        ],
    )
    def test_accepts_documented_utilities_and_their_allowed_prefixes(self, token):
        assert is_allowed_utility_class(token)


# ---------------------------------------------------------------------------
# T021 — i18n guard. FR-007, D-7.
#
# Every literal string a reader sees in a shipped template must be inside
# {% translate %} or {% blocktranslate %}. Scope: text nodes between HTML
# tags. Literal text embedded in a component *attribute* value (for example
# a hard-coded ``title="Foo"``) is out of scope — telling a reader-visible
# attribute like ``title`` apart from a Cotton configuration attribute like
# ``size="sm"`` or ``cols="1"`` is not mechanically decidable from the
# reference material this task was given, the way class-vs-parameter was for
# the guard above. Every attribute-embedded literal string in the six
# shipped templates today already goes through {% translate %} regardless
# (item_detail.html's ``<c-section title="{% translate "Contributors" %}">``
# and its two siblings), so this is a documented gap, not a proven miss.
# ---------------------------------------------------------------------------

_BLOCKTRANSLATE_RE = re.compile(r"\{%\s*blocktranslate\b.*?%\}.*?\{%\s*endblocktranslate\s*%\}", re.DOTALL)
_TRANSLATE_TAG_RE = re.compile(r"\{%\s*trans(?:late)?\s+[\"'][^\"']*[\"']\s*%\}")
_DJANGO_TAG_RE = re.compile(r"\{%.*?%\}", re.DOTALL)
_DJANGO_VAR_RE = re.compile(r"\{\{.*?\}\}", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]*>", re.DOTALL)
_HTML_ENTITY_RE = re.compile(r"&[#a-zA-Z0-9]+;")
_LETTER_RE = re.compile(r"[A-Za-z]")


def reader_visible_residue(source: str) -> str:
    """What is left of ``source``'s text nodes once every already-translated
    span, every other piece of template machinery, and every HTML tag and
    entity is removed — in that order, so a ``{% translate %}`` used inside
    an attribute value (``title="{% translate "Dates" %}"``) is excised
    before the generic tag/HTML stripping ever runs, and so a literal string
    inside an ``{% if %}``/``{% regroup %}`` condition (template logic, not
    reader-facing) is removed with its tag rather than surfacing as residue.
    What remains still carries structural punctuation — ``:``, ``,``,
    ``&middot;``, ``&ndash;`` — because none of it is filtered by name; see
    :func:`has_unwrapped_reader_text`."""
    text = _BLOCKTRANSLATE_RE.sub(" ", source)
    text = _TRANSLATE_TAG_RE.sub(" ", text)
    text = _DJANGO_TAG_RE.sub(" ", text)
    text = _DJANGO_VAR_RE.sub(" ", text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = _HTML_ENTITY_RE.sub(" ", text)
    return text


def has_unwrapped_reader_text(source: str) -> bool:
    """True if any letter survives :func:`reader_visible_residue`. A colon
    separator, the ``&middot;`` separator, the ``&ndash;`` en dash and a
    comma-and-space list join all carry no letters, so they pass through
    without needing to be named as exceptions one at a time — this is a
    generalisation of "colon, middot and whitespace are not reader-facing
    prose", not a narrower reading of it: anything with no letter in it is
    not prose a reader reads as language, wrapped or not."""
    return bool(_LETTER_RE.search(reader_visible_residue(source)))


class TestI18nGuard:
    """T021 — FR-007, D-7. Every literal string a reader sees in a template
    ``literature.ui`` ships is wrapped in ``{% translate %}`` or
    ``{% blocktranslate %}`` — see :func:`has_unwrapped_reader_text` and its
    docstring for what counts as "a reader sees" and what does not."""

    @pytest.mark.parametrize("template_path", TEMPLATE_PATHS, ids=lambda p: p.name)
    def test_no_unwrapped_reader_text(self, template_path):
        source = template_path.read_text()
        residue = reader_visible_residue(source)
        assert not has_unwrapped_reader_text(source), (
            f"{template_path.name}: literal reader-facing text outside "
            f"{{% translate %}}/{{% blocktranslate %}}: {residue!r}"
        )

    def test_detects_a_bare_literal_reader_string(self):
        assert has_unwrapped_reader_text("<c-text>Showing results</c-text>")

    def test_accepts_the_same_string_wrapped_in_translate(self):
        assert not has_unwrapped_reader_text('<c-text>{% translate "Showing results" %}</c-text>')

    def test_accepts_the_same_string_wrapped_in_blocktranslate(self):
        assert not has_unwrapped_reader_text(
            "<c-text>{% blocktranslate %}Showing results{% endblocktranslate %}</c-text>"
        )

    def test_accepts_translate_used_inside_an_attribute_value(self):
        assert not has_unwrapped_reader_text('<c-section title="{% translate "Dates" %}">')

    @pytest.mark.parametrize(
        "fragment",
        [
            "{{ group.grouper }}:",
            "{% if not forloop.last %}, {% endif %}",
            "&middot;",
            "&ndash;",
            "   \n   ",
            "",
        ],
    )
    def test_colon_comma_entities_and_whitespace_do_not_trip_it(self, fragment):
        assert not has_unwrapped_reader_text(fragment)
