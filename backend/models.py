"""Shared data types for the Campus Customs agent team.

Kept deliberately small for now (Problem 5) — this is expected to grow as
more tools and agent behaviors are added in later problems.
"""

from typing import Literal

from pydantic import BaseModel


class AgentReply(BaseModel):
    """The structured output every agent in the team returns, whether it's
    answering the Boss directly or replying to another agent that delegated
    to it. Keeping one shared shape (rather than a bespoke type per agent)
    is what lets any agent delegate to any other agent and parse the reply
    the same way.

    `category` distinguishes why `needs_human_approval` is set, since not
    every approval is about money (a stuck ticket or a frustrated customer
    also needs a human, but there's nothing to pay). `"payment"` and
    `"payment_pending_confirmation"` both carry `payment_amount`/
    `payment_account` -- that's what the approve routes need to move real
    cash; `"review"` is everything else.

    `"payment_pending_confirmation"` is for when an agent has a real amount
    and account ready but can't confirm whether it's already been paid (no
    payment-history tool exists yet) -- rather than silently withholding the
    recommendation, it reports the payment in full and lets a human confirm
    payment status first (`POST /api/approvals/{id}/confirm-payment-status`),
    instead of a blind "approve".
    """

    message: str
    needs_human_approval: bool = False
    recommended_action: str | None = None
    category: Literal["payment", "review", "payment_pending_confirmation"] | None = None
    payment_amount: float | None = None
    payment_account: str | None = None


class TicketRecord(BaseModel):
    """One row from the `tickets` table, read directly from the database
    (not through an MCP tool yet — ticket intake isn't one of the 3 MCP
    tools built in Problem 3). Used to hand the Boss agent a ticket's full
    context as its starting task.
    """

    id: int
    type: str
    requester: str
    subject: str
    sku: str | None
    size: str | None
    qty: int | None
    lease_id: int | None
    invoice_id: int | None
    status: str
    notes: str | None
    created_at: str
