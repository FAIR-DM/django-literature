"""Regression test for the citation-key de-duplication suffix generator (issue #41).

``_generate_dedup_suffix`` lives in ``literature/converters.py``, which ``tests/test_converters.py``
already mirrors — but that file is this feature's own evidence that T005 was a move and not a
rewrite, and this story's prohibitions keep it green and byte-for-byte unmodified (spec 005
tasks.md T041, decisions.md D16). So this narrow regression, testing the generator directly rather
than through ``from_csl_json``, lives in its own module instead of inside the file it must not
touch.

Testing the generator directly, not by driving hundreds of entries through ``from_csl_json``: that
route costs roughly one query per candidate suffix, and at the red step it hangs rather than
failing (tasks.md T041).
"""

import itertools

from literature.converters import _generate_dedup_suffix


class TestGenerateDedupSuffix:
    """Unbounded and non-repeating, with its first 701 values pinned (issue #41)."""

    def test_first_701_values_are_unchanged(self):
        """``tests/test_converters.py``'s own dedup tests pin the start of this sequence
        (``test_deduplication_appends_b``, ``test_deduplication_wrap_around``) — extending it
        must not reorder what they already assert on.
        """
        singles = list("bcdefghijklmnopqrstuvwxyz")
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        pairs = ["".join(combo) for combo in itertools.product(alphabet, repeat=2)]
        expected = singles + pairs
        assert len(expected) == 701

        actual = list(itertools.islice(_generate_dedup_suffix("Smith2009"), 701))
        assert actual == expected

    def test_twenty_thousand_values_are_all_distinct(self):
        """Past the 701st value the sequence used to repeat forever (issue #41): once every
        two-letter suffix had been yielded, the outer ``while True`` started the two-letter
        product over from ``aa`` again, so ``_resolve_citation_key`` never terminated past 701
        collisions on the same base key.
        """
        values = list(itertools.islice(_generate_dedup_suffix("Smith2009"), 20_000))
        assert len(values) == len(set(values))
