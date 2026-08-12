"""The guard's assertion script (plan.md D-5, D-8; FR-017 through FR-022).

Speaks real HTTP against a running demo server. It knows one address — the
catalogue list — and reaches every other page by following the links a
browser would click, never by reversing a detail URL: SC-003 requires every
page to be reachable "with no address typed by hand", and a script that
constructs its own URLs would pass over a catalogue whose links are broken.

Not a test module: standard library only, run directly against a live
server, not under pytest (conventions; constitution Article VII).
"""

import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# The demo runs with DEBUG = True (plan.md D-5): an unbounded body on failure
# would put Django's technical-500 page, including settings and the request
# environment, into a public CI log.
_BODY_EXCERPT_LIMIT = 500

_ITEM_LINK_RE = re.compile(r'href="(?P<path>/catalogue/\d+/)"[^>]*>(?P<text>[^<]+)<')
_CONTRIBUTOR_LINK_RE = re.compile(r'href="(?P<path>/catalogue/contributors/\d+/)"[^>]*>(?P<text>[^<]+)<')
_SECOND_PAGE_LINK_RE = re.compile(r'href="\?page=2"')


class SmokeCheckFailed(Exception):
    """The URL, status and a bounded body excerpt of a failed check (FR-020)."""


class DemoWalk:
    """Walks the demo from its catalogue list, following links only (plan.md D-5)."""

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def run(self):
        list_url = f"{self.base_url}/catalogue/"
        list_body = self._get(list_url)
        item_links = _ITEM_LINK_RE.findall(list_body)
        if not item_links:
            self._fail(list_url, 200, "no reference link on the catalogue list — the seed did not load", list_body)

        if not _SECOND_PAGE_LINK_RE.search(list_body):
            self._fail(list_url, 200, "no second-page link on the catalogue list", list_body)
        second_page_url = f"{list_url}?page=2"
        second_page_body = self._get(second_page_url)
        if not _ITEM_LINK_RE.search(second_page_body):
            self._fail(second_page_url, 200, "no reference link on the catalogue's second page", second_page_body)

        self._walk_to_contributor(item_links)

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

    def _get(self, url):
        """GET url, following redirects, and fail if any lands on a login page (FR-005, T015)."""
        try:
            with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 — http(s) only, built from base_url argv, never external input
                body = response.read().decode("utf-8", errors="replace")
                final_url = response.geturl()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            self._fail(url, exc.code, "unsuccessful response", body)
        except urllib.error.URLError as exc:
            self._fail(url, None, f"could not connect: {exc.reason}")

        # The whole walk is unauthenticated (FR-005) — a redirect to a login
        # page anywhere in it is a failure of that openness, checked rather
        # than assumed.
        if "login" in urllib.parse.urlparse(final_url).path.lower():
            self._fail(url, 200, f"redirected to a login page ({final_url}) on an unauthenticated walk", body)

        return body

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
    print(f"OK: walked the demo catalogue, its second page, a reference and a contributor at {base_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
