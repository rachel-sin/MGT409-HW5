"""Campus Customs desk API -- the backend the React dashboard (Problem 8)
will call. Every route here either reads the shop's real state or, for the
one route that can move money, requires a human to have explicitly clicked
approve first. No route ever calls an LLM directly except the run route,
which hands a ticket to the already-built agent team (team.run_ticket()).
"""

import json
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import payments
import reset_db
import team
from approvals import decide as decide_approval
from approvals import get as get_approval
from approvals import list_pending
from models import AgentReply, TicketRecord
from runtime import REPO_ROOT

CASH_DB_PATH = REPO_ROOT / "data" / "campus_customs_new.db"
AUDIT_LOG_PATH = REPO_ROOT / "output" / "audit_trail.json"

app = FastAPI(title="Campus Customs Desk API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApproveRequest(BaseModel):
    decided_by: str


class ConfirmPaymentStatusRequest(BaseModel):
    already_paid: bool
    decided_by: str


def _payment_kind_and_ref(ticket: TicketRecord) -> tuple[str, int | None]:
    """A payment's `kind`/`ref_id` come from the ticket's own fields, never
    asked of the model -- both approve routes derive it the same way."""
    if ticket.lease_id is not None:
        return "rent", ticket.lease_id
    if ticket.invoice_id is not None:
        return "invoice", ticket.invoice_id
    return "other", None


class AgentEvent(BaseModel):
    ticket_id: int | None
    agent: str
    message: str | None = None
    needs_human_approval: bool | None = None
    category: str | None = None
    tool_calls: list[dict] = []
    timestamp: str


class CashBalance(BaseModel):
    name: str
    balance: float
    date: str


@app.get("/api/tickets", response_model=list[TicketRecord])
def get_tickets() -> list[TicketRecord]:
    """The three tickets and whether each is open or resolved."""
    return team.list_tickets()


@app.post("/api/tickets/{ticket_id}/run", response_model=AgentReply)
def run_ticket(ticket_id: int) -> AgentReply:
    """Hand this ticket to the real agent team (Boss + whoever it
    delegates to) and return its final reply. This is the first route that
    actually calls the live Portkey API."""
    try:
        return team.run_ticket(ticket_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/tickets/{ticket_id}/live")
def get_live_run(ticket_id: int) -> dict:
    """Real-time progress for a run that's still in flight -- the same
    in-memory trace team.run_ticket() is building, not a simulation.
    Boss's own reasoning/tool calls only land here once the whole run
    finishes (it's one blocking call), but every delegated specialist's
    step appears the moment it completes. Meant to be polled every second
    or so while a run is in progress."""
    return {"running": team.is_running(ticket_id), "steps": team.get_live_steps(ticket_id)}


@app.get("/api/events", response_model=list[AgentEvent])
def get_events(limit: int = 20) -> list[AgentEvent]:
    """The most recent agent events -- what each agent said and which
    tools it used -- flattened out of output/audit_trail.json so the
    dashboard can refresh and show what just happened."""
    if not AUDIT_LOG_PATH.exists():
        return []
    try:
        entries = json.loads(AUDIT_LOG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    events: list[AgentEvent] = []
    for entry in entries:
        if entry.get("event") == "reset":
            events.append(
                AgentEvent(
                    ticket_id=None,
                    agent="system",
                    message=f"Database reset -- previous state archived to {entry.get('archived_to')}.",
                    timestamp=entry["timestamp"],
                )
            )
            continue
        ticket_id = entry.get("ticket_id")
        timestamp = entry.get("timestamp")
        boss_reply = entry.get("boss_reply") or {}
        events.append(
            AgentEvent(
                ticket_id=ticket_id,
                agent="boss",
                message=boss_reply.get("message"),
                needs_human_approval=boss_reply.get("needs_human_approval"),
                category=boss_reply.get("category"),
                tool_calls=entry.get("boss_tool_calls") or [],
                timestamp=timestamp,
            )
        )
        for call in entry.get("delegated_agent_calls") or []:
            events.append(
                AgentEvent(
                    ticket_id=ticket_id,
                    agent=call.get("agent", "unknown"),
                    message=call.get("message"),
                    needs_human_approval=call.get("needs_human_approval"),
                    category=call.get("category"),
                    tool_calls=call.get("tool_calls") or [],
                    timestamp=timestamp,
                )
            )

    return events[-limit:]


@app.get("/api/approvals")
def get_approvals(ticket_id: int | None = None) -> list[dict]:
    """Pending approvals -- the dashboard needs an approval's real `id`
    before it can call the approve route below; nothing in a ticket's own
    AgentReply carries that id."""
    pending = list_pending()
    if ticket_id is not None:
        pending = [p for p in pending if p["ticket_id"] == ticket_id]
    return pending


@app.post("/api/approvals/{approval_id}/approve")
def approve(approval_id: int, body: ApproveRequest) -> dict:
    """Approve a payment -- the ONLY route that actually changes cash.
    Agents only ever prepare/recommend a payment (category="payment" on
    their AgentReply); a human clicking approve here is what moves real
    money. Only acts on "payment" category approvals -- a "review"
    approval (nothing to do with money) isn't something this route can act
    on at all."""
    try:
        entry = get_approval(approval_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if entry["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Approval {approval_id} is already {entry['status']}.")
    if entry.get("category") != "payment":
        raise HTTPException(
            status_code=400,
            detail=f"Approval {approval_id} is a {entry.get('category')!r} approval, not a payment -- nothing to pay.",
        )

    ticket = team.load_ticket(entry["ticket_id"])
    kind, ref_id = _payment_kind_and_ref(ticket)

    payment = payments.apply_payment(
        amount=entry["payment_amount"],
        account=entry["payment_account"],
        kind=kind,
        ref_id=ref_id,
        approved_by=body.decided_by,
    )
    decided = decide_approval(approval_id, True, body.decided_by)
    team.mark_ticket_status(entry["ticket_id"], "resolved")

    return {"approval": decided, "payment": payment}


@app.post("/api/approvals/{approval_id}/confirm-payment-status")
def confirm_payment_status(approval_id: int, body: ConfirmPaymentStatusRequest) -> dict:
    """Resolves a "payment_pending_confirmation" entry -- Accounting has a
    real amount/account ready but couldn't confirm whether it was already
    paid (no payment-history tool exists), so a human answers that one
    question instead of approving blind. Not already paid: behaves exactly
    like a normal approval (moves the cash). Already paid: nothing is paid
    (no duplicate), but the ticket still resolves, since the open question
    is now answered either way."""
    try:
        entry = get_approval(approval_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if entry["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Approval {approval_id} is already {entry['status']}.")
    if entry.get("category") != "payment_pending_confirmation":
        raise HTTPException(
            status_code=400,
            detail=f"Approval {approval_id} is a {entry.get('category')!r} approval, not a payment-status check.",
        )

    payment = None
    if body.already_paid:
        decided = decide_approval(approval_id, False, body.decided_by)
    else:
        ticket = team.load_ticket(entry["ticket_id"])
        kind, ref_id = _payment_kind_and_ref(ticket)
        payment = payments.apply_payment(
            amount=entry["payment_amount"],
            account=entry["payment_account"],
            kind=kind,
            ref_id=ref_id,
            approved_by=body.decided_by,
        )
        decided = decide_approval(approval_id, True, body.decided_by)

    team.mark_ticket_status(entry["ticket_id"], "resolved")

    return {"approval": decided, "payment": payment}


@app.get("/api/cash", response_model=CashBalance)
def get_cash(account_name: str = "checking") -> CashBalance:
    """The current real balance in cash_accounts."""
    conn = sqlite3.connect(CASH_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account_name,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No cash account named {account_name!r}.")
    return CashBalance(**dict(row))


@app.post("/api/reset")
def reset() -> dict:
    """Archive the current working database + pending approvals, then
    rebuild a fresh working copy from the untouched original seed. Never
    touches output/audit_trail.json except to append one marker entry."""
    return reset_db.reset_database()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
