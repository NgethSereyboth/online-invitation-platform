"""Resource-scoped permission grants — Grant grammar + matcher.

V54.15 (sec-6 — §2.6) Stage 3.  Replaces the coarse tier-based
``read``/``edit``/``manage``/``admin`` permission model with
resource-scoped grants like ``event:{id}:publish`` and
``template:install``.

This module is intentionally pure (no I/O).  The runtime queries the
``agent_grants`` table (see ``capabilities.build_access_snapshot``) and
hands the resulting rows to ``evaluate`` here.

Grammar (per ``docs/ai/RESOURCE-SCOPED-PERMISSIONS.md`` §2.1, simplified
for Stage 3 — sub_resource / sub_id are deferred to Phase 1b)::

    {resource_type}:{resource_id}:{action}      # 3-part form
    {resource_type}:{action}                    # 2-part form (resource_id="*")

The 2-part form is sugar for ``{resource_type}:*:{action}`` — i.e. a
wildcard on the resource id.  Examples::

    event:123:publish       # publish permission on event 123
    event:*:publish         # publish permission on ANY event
    template:install        # install permission on any template
    guest:42:delete         # delete permission on guest 42

Matching rules (``Grant.matches(other)`` — ``self`` is the granted
permission, ``other`` is the required permission being checked):

* ``resource_type`` must be exactly equal.
* ``resource_id`` matches if ``self.resource_id == "*"`` OR
  ``self.resource_id == other.resource_id``.
* ``action`` matches if ``self.action == "*"`` OR
  ``self.action == other.action``.

Test coverage lives in ``tests/ai_resource_scopes_test.py``.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Iterable


# Allowed token characters: lowercase letters, digits, hyphens.  The
# resource_id is more permissive — it carries invitation ids, event ids,
# template ids (which can contain ``-`` and digits) but is bounded by the
# ``[^:]+`` character class so it cannot contain a colon (which would
# re-split into more parts).
_RESOURCE_TYPE_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_RESOURCE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
_ACTION_RE = re.compile(r"^[a-z][a-z0-9-]*$")
# A 2-part grant has no resource_id segment — the parser substitutes "*".
_TWO_PART = 2
_THREE_PART = 3


class GrantParseError(ValueError):
    """Raised when a grant string does not match the grammar."""


@dataclass(frozen=True)
class Grant:
    """A single resource-scoped permission grant.

    ``resource_type`` — the kind of resource (``event``, ``invitation``,
    ``template``, ``plugin``, ``account``, ``workspace``).
    ``resource_id`` — the specific resource identifier, or ``"*"`` for
    "any resource of this type".
    ``action`` — the verb (``read``, ``edit``, ``publish``, ``archive``,
    ``install``, ``delete``, ...).
    """

    resource_type: str
    resource_id: str
    action: str

    @classmethod
    def parse(cls, grant_str: str) -> "Grant":
        """Parse a grant string into a :class:`Grant` instance.

        Accepts both the 3-part form ``type:id:action`` and the 2-part
        form ``type:action`` (the latter desugars to ``type:*:action``).
        Raises :class:`GrantParseError` on malformed input.
        """
        text = str(grant_str or "").strip()
        if not text:
            raise GrantParseError("Empty grant string")
        if text.count(":") == _TWO_PART - 1:
            # 2-part form: type:action → type:*:action
            resource_type, action = text.split(":", 1)
            resource_id = "*"
        elif text.count(":") == _THREE_PART - 1:
            resource_type, resource_id, action = text.split(":", 2)
        else:
            raise GrantParseError(
                f"Invalid grant syntax: {grant_str!r} — expected 'type:id:action' or 'type:action'"
            )
        resource_type = resource_type.strip()
        resource_id = resource_id.strip()
        action = action.strip()
        if not resource_type or not _RESOURCE_TYPE_RE.fullmatch(resource_type):
            raise GrantParseError(
                f"Invalid resource_type: {resource_type!r} — must match {_RESOURCE_TYPE_RE.pattern}"
            )
        if resource_id != "*" and (not resource_id or not _RESOURCE_ID_RE.fullmatch(resource_id)):
            raise GrantParseError(
                f"Invalid resource_id: {resource_id!r} — must be '*' or match {_RESOURCE_ID_RE.pattern}"
            )
        if not action or not _ACTION_RE.fullmatch(action):
            raise GrantParseError(
                f"Invalid action: {action!r} — must match {_ACTION_RE.pattern}"
            )
        return cls(resource_type, resource_id, action)

    def matches(self, other: "Grant") -> bool:
        """Return True if ``self`` (the granted permission) covers ``other``
        (the required permission being checked).

        A grant covers a requirement iff:
        * resource_type is exactly equal, AND
        * self.resource_id is ``"*"`` OR equals other.resource_id, AND
        * self.action is ``"*"`` OR equals other.action.
        """
        if self.resource_type != other.resource_type:
            return False
        if self.resource_id != "*" and self.resource_id != other.resource_id:
            return False
        if self.action != "*" and self.action != other.action:
            return False
        return True

    def __str__(self) -> str:
        if self.resource_id == "*":
            return f"{self.resource_type}:{self.action}"
        return f"{self.resource_type}:{self.resource_id}:{self.action}"

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        return f"Grant({self.resource_type!r}, {self.resource_id!r}, {self.action!r})"


def parse_grants(grant_strings: Iterable[str]) -> list[Grant]:
    """Parse a list of grant strings into :class:`Grant` instances.

    Invalid entries are skipped (a warning is logged via the standard
    ``warnings`` module) so a single bad row in ``agent_grants`` cannot
    break the entire availability check.
    """
    import warnings

    out: list[Grant] = []
    for raw in grant_strings:
        try:
            out.append(Grant.parse(raw))
        except GrantParseError as exc:
            warnings.warn(f"Skipping malformed grant {raw!r}: {exc}", stacklevel=2)
    return out


def evaluate(
    grants: Iterable[Grant],
    required_resource_type: str,
    required_resource_id: str,
    required_action: str,
) -> bool:
    """Return True if ANY grant in ``grants`` covers the required permission.

    This is the pure (no-I/O) entry point used by the runtime grant
    check in ``capabilities.availability``.  The grants list is built by
    ``build_access_snapshot`` from the ``agent_grants`` table rows for
    the current user.
    """
    try:
        required = Grant(required_resource_type, required_resource_id, required_action)
    except (GrantParseError, ValueError) as exc:
        # Defensive: if the runtime passes a malformed requirement
        # (e.g. tool id with uppercase letters), fail closed.
        raise GrantParseError(
            f"Invalid required permission: {required_resource_type!r}:"
            f"{required_resource_id!r}:{required_action!r}: {exc}"
        ) from exc
    return any(g.matches(required) for g in grants)
