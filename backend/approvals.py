"""A durable record of every agent decision flagged for human review.

`needs_human_approval` on an AgentReply is self-reported by the model --
nothing stops an agent from simply failing to set it on something that
should have required approval, and nothing stops a future caller from just
reading the boolean and forgetting about it. Recording it here, *unconditionally*,
whenever team.run_ticket() sees that flag, turns it into a real persisted
checkpoint a human must explicitly act on, instead of a value that could be
silently dropped.

This gates the ticket *decision* itself. PydanticAI has a separate, native
mechanism for gating an actual tool *call* mid-run --
`toolset.approval_required(...)` paired with `DeferredToolResults` -- which
pauses execution until a human approves it before the tool's effect ever
happens. That's the right tool for the job the moment this system adds a
tool that actually executes something (a payment, a discount, a restock
order). All 3 of today's MCP tools are read-only lookups, so there's
nothing to gate at the tool-call level yet.
"""

import json
from datetime import datetime, timezone

from runtime import REPO_ROOT

APPROVALS_PATH = REPO_ROOT / "output" / "pending_approvals.json"


def _load() -> list[dict]:
    if not APPROVALS_PATH.exists():
        return []
    try:
        return json.loads(APPROVALS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list[dict]) -> None:
    APPROVALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPROVALS_PATH.write_text(json.dumps(entries, indent=2, default=str))


def record_pending_approval(
    ticket_id: int,
    message: str,
    recommended_action: str | None,
    category: str | None = None,
    payment_amount: float | None = None,
    payment_account: str | None = None,
) -> int:
    """Unconditionally persist a decision that needs human sign-off.
    Returns the new entry's id. Not optional -- run_ticket() calls this
    every time a final reply has needs_human_approval=True, regardless of
    whether anything downstream also checks the flag.

    `category` distinguishes a real-money "payment" entry (which carries
    `payment_amount`/`payment_account` and is the only kind the approve
    route in main.py will actually act on) from a "review" entry -- a
    ticket Boss got stuck on, or a frustrated customer -- which has no
    money to move."""
    entries = _load()
    approval_id = max((entry["id"] for entry in entries), default=0) + 1
    entries.append(
        {
            "id": approval_id,
            "ticket_id": ticket_id,
            "message": message,
            "recommended_action": recommended_action,
            "category": category,
            "payment_amount": payment_amount,
            "payment_account": payment_account,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decided_at": None,
            "decided_by": None,
        }
    )
    _save(entries)
    return approval_id


def decide(approval_id: int, approved: bool, decided_by: str) -> dict:
    """The only way a pending entry leaves the "pending" state -- a named
    human explicitly approves or rejects it. No code path marks an entry
    approved on its own."""
    entries = _load()
    for entry in entries:
        if entry["id"] == approval_id:
            if entry["status"] != "pending":
                raise ValueError(f"Approval {approval_id} was already {entry['status']}")
            entry["status"] = "approved" if approved else "rejected"
            entry["decided_at"] = datetime.now(timezone.utc).isoformat()
            entry["decided_by"] = decided_by
            _save(entries)
            return entry
    raise ValueError(f"No pending approval with id {approval_id}")


def list_pending() -> list[dict]:
    """Only a ticket's current, live approval -- found by taking each
    ticket's single most recent entry overall (any status), then keeping it
    here only if that one is still pending. A ticket run more than once can
    leave an older entry behind that was never explicitly decided one way or
    the other (so it's never deleted or rewritten here) -- but once a later
    run's own entry has itself been decided, the older one shouldn't
    resurface as if it were still the ticket's live approval."""
    entries = _load()
    latest_per_ticket: dict[int, dict] = {}
    for entry in entries:
        ticket_id = entry["ticket_id"]
        if ticket_id not in latest_per_ticket or entry["created_at"] > latest_per_ticket[ticket_id]["created_at"]:
            latest_per_ticket[ticket_id] = entry
    return [entry for entry in latest_per_ticket.values() if entry["status"] == "pending"]


def get(approval_id: int) -> dict:
    for entry in _load():
        if entry["id"] == approval_id:
            return entry
    raise ValueError(f"No approval with id {approval_id}")
