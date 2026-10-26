# ADR 0036 — Writing asks for a model permission

**Status:** accepted. Supersedes [ADR 0022](0022-the-front-ends-pages-are-open.md).

## Decision

Each page in the front end that changes the catalogue requires the Django model permission for
what it does:

| Pages | Permission |
|---|---|
| Add, and every import page (form, preview, restart, confirm) | `literature.add_item` |
| Edit | `literature.change_item` |
| Delete | `literature.delete_item` |

A visitor who is not signed in is sent to the project's `LOGIN_URL`. A signed-in user without the
permission is refused with a 403. The Add, Import, Edit and Delete actions are drawn only for a
user who holds the permission behind them.

The read pages stay open: the catalogue, a reference's page and a contributor's page.

## Why

ADR 0022 left every page open on the assumption of one person managing their own library, and named
when to revisit it: once the package is used by more than one person against the same store, or
exposed beyond a trusted network. Both now hold. Projects embed the catalogue in multi-user sites,
where mounting `literature.ui.urls` let anyone empty it.

Django's model permissions are what a host already uses for everything else, so this adds no model
of its own. A host grants the three permissions to a group, and a superuser holds them already.
Importing creates references, so it asks for the same permission as adding one.

A host that wants a different rule, such as object-level permissions, subclasses the view and
replaces `permission_required` or `has_permission()`. A setting for it is not added until a host
needs one.

## Consequences

- The import page's upload (ADR 0030) is now accepted only from users holding
  `literature.add_item`. It is still unbounded by the package itself.
- The demo creates an editor account when it is seeded, and signs in through its admin.
