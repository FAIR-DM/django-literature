"""The guard's assertion script (plan.md D-5, D-8, D-9; FR-017 through FR-022, FR-032, FR-033).

Speaks real HTTP against a running demo server. It knows one address — the
catalogue list — and reaches every other page by following the links a
browser would click, never by reversing a detail URL: SC-003 requires every
page to be reachable "with no address typed by hand", and a script that
constructs its own URLs would pass over a catalogue whose links are broken.

Not a test module: standard library only, run directly against a live
server, not under pytest (conventions; constitution Article VII).
"""

import http.cookiejar
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from html.parser import HTMLParser

# The demo runs with DEBUG = True (plan.md D-5): an unbounded body on failure
# would put Django's technical-500 page, including settings and the request
# environment, into a public CI log.
_BODY_EXCERPT_LIMIT = 500

_ITEM_LINK_RE = re.compile(r'href="(?P<path>/catalogue/\d+/)"[^>]*>(?P<text>[^<]+)<')
_CONTRIBUTOR_LINK_RE = re.compile(r'href="(?P<path>/catalogue/contributors/\d+/)"[^>]*>(?P<text>[^<]+)<')

# Today's pagination component replaces the whole query string on every page
# link (plan.md D-14, tracked upstream as django-mvp/django-mvp#270 and here
# as #88), so a rendered link is always the bare `?page=2`. This pattern
# tolerates the link carrying other parameters either side of `page=2` so it
# stays correct once that defect is fixed and a sort survives the page move,
# without also matching a link that carries no page parameter at all.
_SECOND_PAGE_LINK_RE = re.compile(r'href="(?P<query>\?(?:[^"]*&)?page=2(?:&[^"]*)?)"')

# The write pass's own links (T021, D-9): the catalogue's Add action, and a
# reference page's Edit and Delete actions. Unlike the two patterns above,
# these do not capture link text — the button's visible text sits behind an
# icon element (mvp's <c-button>), not immediately after the href's closing
# ``>``, and the write pass only needs the address.
_CREATE_LINK_RE = re.compile(r'href="(?P<path>/catalogue/add/)"')
_EDIT_LINK_RE = re.compile(r'href="(?P<path>/catalogue/\d+/update/)"')
_DELETE_LINK_RE = re.compile(r'href="(?P<path>/catalogue/\d+/delete/)"')


class _FormFieldParser(HTMLParser):
    """Field name → current value for the first ``<form>`` on a page (T021, D-9).

    Walks ``input``, ``select``/``option`` and ``textarea`` tags the way a
    browser's own form submission would: an element with no ``name``
    attribute contributes nothing (that is how ``item_form.html``'s "Show
    every field" toggle, which carries no ``name``, stays off the wire), a
    ``select``'s value is whichever ``option`` carries ``selected`` or
    otherwise its first option (a browser's own default), and a
    ``textarea``'s value is its text content. This is what lets a caller post
    the whole form back with one field changed rather than build a payload by
    hand — posting only the changed field blanks the rest, for the
    ``construct_instance`` reason plan.md D-3 states.
    """

    def __init__(self):
        super().__init__()
        self.fields: dict[str, str] = {}
        self._in_form = False
        # Set once the first form closes, so a second form on the page
        # contributes nothing. Without it this reads the union of every form,
        # and the token it keeps is whichever came last.
        self._first_form_done = False
        self._current_select: str | None = None
        self._selects_with_an_option_seen: set[str] = set()
        self._current_textarea: str | None = None
        self._textarea_chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == "form":
            if not self._first_form_done:
                self._in_form = True
            return
        if not self._in_form:
            return

        if tag == "input":
            name = attr_dict.get("name")
            if not name:
                return
            input_type = attr_dict.get("type", "text")
            if input_type in ("submit", "button", "reset", "image"):
                return
            if input_type in ("checkbox", "radio"):
                if "checked" in attr_dict:
                    self.fields[name] = attr_dict.get("value", "on")
                return
            self.fields[name] = attr_dict.get("value", "")
        elif tag == "select":
            self._current_select = attr_dict.get("name")
            if self._current_select:
                self.fields.setdefault(self._current_select, "")
        elif tag == "option":
            if self._current_select is None:
                return
            value = attr_dict.get("value", "")
            # The first option is the fallback a browser selects when nothing
            # is marked `selected`; a later `selected` option always wins,
            # matching how a browser resolves more than one (the last one).
            if self._current_select not in self._selects_with_an_option_seen:
                self.fields[self._current_select] = value
                self._selects_with_an_option_seen.add(self._current_select)
            if "selected" in attr_dict:
                self.fields[self._current_select] = value
        elif tag == "textarea":
            self._current_textarea = attr_dict.get("name")
            self._textarea_chunks = []
            if self._current_textarea:
                self.fields.setdefault(self._current_textarea, "")

    def handle_endtag(self, tag):
        if tag == "form":
            if self._in_form:
                self._first_form_done = True
            self._in_form = False
        elif tag == "select":
            self._current_select = None
        elif tag == "textarea":
            if self._current_textarea:
                value = "".join(self._textarea_chunks)
                # A textarea's HTML content model ignores one leading newline
                # right after the opening tag (the HTML spec's own rule,
                # which every browser applies) — Django's widget template
                # writes one for readability, and without stripping it here
                # every round-tripped textarea value would grow a newline
                # the stored value never had.
                if value.startswith("\n"):
                    value = value[1:]
                self.fields[self._current_textarea] = value
            self._current_textarea = None
            self._textarea_chunks = []

    def handle_data(self, data):
        if self._current_textarea is not None:
            self._textarea_chunks.append(data)


def _form_fields(body: str) -> dict[str, str]:
    """The name → value pairs the first ``<form>`` in ``body`` would post (T021, D-9)."""
    parser = _FormFieldParser()
    parser.feed(body)
    return parser.fields


class SmokeCheckFailed(Exception):
    """The URL, status and a bounded body excerpt of a failed check (FR-020)."""


class DemoWalk:
    """Walks the demo from its catalogue list, following links only (plan.md D-5, D-9).

    ``self.opener`` is built once and reused for every request the walk
    makes, read or write (T021). A create or edit form sets a CSRF cookie
    while it is GET'd, and the walk's own POST back to that same form has to
    carry it — two independent ``urlopen`` calls would not share that state,
    so one ``HTTPCookieProcessor``-backed opener carries it across the whole
    walk instead.
    """

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def run(self):
        list_url = f"{self.base_url}/catalogue/"
        list_body = self._get(list_url)
        item_links = _ITEM_LINK_RE.findall(list_body)
        if not item_links:
            self._fail(list_url, 200, "no reference link on the catalogue list — the seed did not load", list_body)

        second_page_match = _SECOND_PAGE_LINK_RE.search(list_body)
        if second_page_match is None:
            self._fail(list_url, 200, "no second-page link on the catalogue list", list_body)
        second_page_url = f"{list_url}{second_page_match.group('query')}"
        second_page_body = self._get(second_page_url)
        if not _ITEM_LINK_RE.search(second_page_body):
            self._fail(second_page_url, 200, "no reference link on the catalogue's second page", second_page_body)

        self._walk_to_contributor(item_links)
        self._walk_write_pass(list_url, list_body)

    def _walk_to_contributor(self, item_links):
        """Follow the list's reference links in order until one has a contributor (plan.md D-5)."""
        tried = []
        for path, title in item_links:
            item_url = f"{self.base_url}{path}"
            tried.append(item_url)
            item_body = self._get(item_url)
            if title not in item_body:
                self._fail(item_url, 200, f"reference page does not carry the catalogue's title {title!r}", item_body)

            contributor_match = _CONTRIBUTOR_LINK_RE.search(item_body)
            if contributor_match is None:
                continue

            contributor_path = contributor_match.group("path")
            contributor_name = contributor_match.group("text")
            contributor_url = f"{self.base_url}{contributor_path}"
            contributor_body = self._get(contributor_url)
            if contributor_name not in contributor_body:
                self._fail(
                    contributor_url,
                    200,
                    f"contributor page does not carry the credited name {contributor_name!r}",
                    contributor_body,
                )
            return

        self._fail(
            self.base_url,
            None,
            f"none of {len(tried)} reference page(s) carried a contributor link: {', '.join(tried)}",
        )

    def _walk_write_pass(self, list_url, list_body):
        """Create, correct and remove a reference over HTTP (T021, D-9).

        Follows the catalogue's own Add/Edit/Delete links, the same
        discipline the read walk above uses — no address is typed by hand
        (SC-003). Every POST carries the whole rendered form back with only
        the field this step claims to change, built by ``_form_fields``: a
        bare field dict would blank the other fields for the
        ``construct_instance`` reason plan.md D-3 states, which is exactly
        the defect this pass exists to catch, and correcting a field this
        way is also the over-HTTP proof of D-3's no-loss guarantee (SC-003).
        Each step asserts the catalogue changed as it claims, never just that
        a page returned 200 (FR-032, ADR-0018).
        """
        create_match = _CREATE_LINK_RE.search(list_body)
        if create_match is None:
            self._fail(list_url, 200, "no Add link on the catalogue list", list_body)
        create_url = f"{self.base_url}{create_match.group('path')}"

        create_form_body = self._get(create_url)
        fields = _form_fields(create_form_body)
        title = f"Smoke Test Reference {uuid.uuid4().hex[:8]}"
        citation_key = f"smoke-{uuid.uuid4().hex[:8]}"
        fields["type"] = "book"
        fields["title"] = title
        fields["citation_key"] = citation_key
        detail_body, detail_url = self._post(create_url, create_url, fields)
        item_path = urllib.parse.urlparse(detail_url).path
        if not re.fullmatch(r"/catalogue/\d+/", item_path):
            self._fail(
                detail_url,
                200,
                f"creating a reference did not redirect to its own page (landed on {detail_url})",
                detail_body,
            )
        if title not in detail_body:
            self._fail(detail_url, 200, f"created reference's page does not carry its own title {title!r}", detail_body)

        list_after_create = self._get(list_url)
        listed_paths = [path for path, _text in _ITEM_LINK_RE.findall(list_after_create)]
        if item_path not in listed_paths:
            self._fail(
                list_url,
                200,
                f"catalogue list does not list the just-created reference at {item_path}",
                list_after_create,
            )

        edit_match = _EDIT_LINK_RE.search(detail_body)
        if edit_match is None:
            self._fail(detail_url, 200, "no Edit link on the created reference's page", detail_body)
        edit_url = f"{self.base_url}{edit_match.group('path')}"

        edit_form_body = self._get(edit_url)
        edit_fields = _form_fields(edit_form_body)
        corrected_title = f"{title} (corrected)"
        edit_fields["title"] = corrected_title
        updated_body, updated_url = self._post(edit_url, edit_url, edit_fields)
        if urllib.parse.urlparse(updated_url).path != item_path:
            self._fail(
                updated_url,
                200,
                f"correcting a reference did not redirect to its own page (landed on {updated_url})",
                updated_body,
            )
        if corrected_title not in updated_body:
            self._fail(
                updated_url,
                200,
                f"corrected reference's page does not carry the new title {corrected_title!r}",
                updated_body,
            )
        if citation_key not in updated_body:
            self._fail(
                updated_url,
                200,
                f"corrected reference's page lost its citation key {citation_key!r} — "
                "the edit posted a partial form and blanked a field it did not mean to change",
                updated_body,
            )

        delete_match = _DELETE_LINK_RE.search(updated_body)
        if delete_match is None:
            self._fail(updated_url, 200, "no Delete link on the corrected reference's page", updated_body)
        delete_url = f"{self.base_url}{delete_match.group('path')}"

        delete_form_body = self._get(delete_url)
        delete_fields = _form_fields(delete_form_body)
        list_after_delete, _final_url = self._post(delete_url, delete_url, delete_fields)
        remaining_paths = [path for path, _text in _ITEM_LINK_RE.findall(list_after_delete)]
        if item_path in remaining_paths:
            self._fail(
                list_url, 200, f"catalogue list still lists the deleted reference at {item_path}", list_after_delete
            )

    def _get(self, url):
        """GET url, following redirects, and fail if any lands on a login page (FR-005, T015)."""
        body, _final_url = self._fetch(url, url)
        return body

    def _post(self, url, referer, fields):
        """POST fields to url through the walk's shared opener (T021, D-9).

        ``referer`` is the page the form was rendered on — the walk always
        posts a create or edit form back to the address it was fetched from,
        so callers pass the same URL for both, but keeping the parameter
        named for what it is documents why a ``Referer`` header is sent at
        all: the demo's ``CsrfViewMiddleware`` only needs a CSRF cookie over
        plain HTTP, but sending ``Referer`` too matches what a browser
        actually sends and is what plan.md D-9 specifies.

        Returns ``(body, final_url)`` — a caller asserts where the response
        landed as well as what it carries, since create and edit are
        supposed to land back on the reference and delete on the catalogue.
        """
        data = urllib.parse.urlencode(fields).encode("ascii")
        request = urllib.request.Request(url, data=data, headers={"Referer": referer})  # noqa: S310 — http(s) only, built from base_url argv, never external input
        return self._fetch(request, url)

    def _fetch(self, request, display_url):
        """Send request — a URL string or a ``urllib.request.Request`` — through the shared opener.

        Fails if the response is unsuccessful or lands on a login page
        (FR-005). ``display_url`` is what a failure reports: a ``Request``
        knows its own address too, but passing it explicitly keeps this
        method from needing to special-case which kind of argument it got.
        """
        try:
            with self.opener.open(request, timeout=10) as response:
                body = response.read().decode("utf-8", errors="replace")
                final_url = response.geturl()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            self._fail(display_url, exc.code, "unsuccessful response", body)
        except urllib.error.URLError as exc:
            self._fail(display_url, None, f"could not connect: {exc.reason}")

        # The whole walk is unauthenticated (FR-005) — a redirect to a login
        # page anywhere in it is a failure of that openness, checked rather
        # than assumed.
        if "login" in urllib.parse.urlparse(final_url).path.lower():
            self._fail(display_url, 200, f"redirected to a login page ({final_url}) on an unauthenticated walk", body)

        return body, final_url

    def _fail(self, url, status, reason, body=""):
        excerpt = body[:_BODY_EXCERPT_LIMIT]
        raise SmokeCheckFailed(f"{url} [{status}]: {reason}\n{excerpt}")


def main(argv):
    base_url = argv[1] if len(argv) > 1 else "http://127.0.0.1:8000"
    try:
        DemoWalk(base_url).run()
    except SmokeCheckFailed as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        f"OK: walked the demo catalogue, its second page, a reference and a contributor, and created/corrected/removed a reference, at {base_url}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
