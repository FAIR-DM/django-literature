# ADR 0026 — A format accepts a text or a binary handle

**Status:** accepted

## Decision

Every shipped format's `parse` accepts a file handle that reads either `str` or `bytes`, and
decodes bytes itself. `import_file` still passes the handle through untouched, so decoding remains
the format's own job (ADR-0012) — what changes is that a format no longer gets to require one mode
and reject the other.

BibTeX decodes a bytes read as `utf-8-sig`; RIS keeps the decoding it already had and lets a text
read pass through. Both raise the same shaped parse error, naming the encoding and the failing byte
offset, when a bytes read cannot be decoded.

A format added later follows the same rule.

## Why

The two shipped formats had each documented a mode and picked a different one. BibTeX required text
and raised `TypeError: cannot use a string pattern on a bytes-like object` on bytes. RIS required
bytes and raised `AttributeError: 'str' object has no attribute 'decode'` on text. Neither reached
the caller, because the runner catches everything, so each surfaced as one failed entry whose
stated reason was a Python type error.

A file arriving over HTTP is always bytes. That made the mismatch load-bearing the moment anything
but a test called a format: half the shipped formats would fail every upload, with a reason no
reader could act on.

The alternative was for each caller to learn which mode each format wants and open the file
accordingly. That puts a reading decision in every caller, breaks for any format a project
configures itself, and gets the responsibility backwards — the format is the only thing that knows
its own encoding conventions, which is the whole point of ADR-0012.

Accepting both costs one branch on the type of the read, in each format, next to the decoding that
already lives there.

## Revisit if

A format appears whose failure reporting genuinely needs the raw bytes and cannot say anything
useful about an already-decoded read. The rule then becomes that a format may refuse a text handle,
and it says so, and any caller that cannot supply bytes gets a stated error rather than a type
error.
