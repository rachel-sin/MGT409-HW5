"""Wires full connectivity across the 5-agent team: every agent gets a tool
to delegate to every other agent. Built here, not in each agent's own file,
so the agent modules never import each other directly -- an agent-imports-
agent setup would be circular (boss.py importing inventory.py, which
imports boss.py, ...).

Also exposes run_ticket(), which hands one open ticket from the database
straight to the Boss agent. Not run yet -- Problem 5 only builds the team;
exercising this against the live Portkey API is for a later problem.
"""

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timezone

from pydantic import BaseModel
from pydantic_ai import ModelRetry, RunContext, UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, RetryPromptPart, ToolCallPart, ToolReturnPart

from accounting import accounting_agent
from approvals import record_pending_approval
from boss import boss_agent
from customer_service import customer_service_agent
from delegation import MAX_CHAIN_LENGTH, DelegationDeps
from facilities import facilities_agent
from inventory import inventory_agent
from models import AgentReply, TicketRecord
from runtime import REPO_ROOT

DB_PATH = REPO_ROOT / "data" / "campus_customs_new.db"
AUDIT_LOG_PATH = REPO_ROOT / "output" / "audit_trail.json"

# Caps how many steps (tool calls + reasoning turns) a single agent run can
# take before it's treated as stuck in a loop rather than genuinely working.
# A real "timeout" here means too many back-and-forth steps, not wall-clock
# time -- that's what actually indicates an agent looping.
AGENT_STEP_LIMIT = 8

# AGENT_STEP_LIMIT is per agent, not pooled across a delegation chain (fixed
# a real bug where it used to be pooled -- see _make_delegate_tool). That's
# correct, but it means there's no longer any built-in ceiling on a whole
# ticket's total wall-clock time: Boss can use up to 8 of its own real API
# round trips, and whichever specialist it delegates to can ALSO use up to
# 8 of its own, and so on. This is the actual backstop -- a hard cap on the
# whole run, independent of how many agents or steps were involved.
TOTAL_RUN_TIMEOUT_SECONDS = 60

# PydanticAI's own run_sync() uses loop.run_until_complete() on one
# persistent loop, never closing it -- that's deliberate, since the MCP
# client's connection gets bound to whichever event loop it first connects
# on. Using asyncio.run() instead (which always creates AND closes a fresh
# loop every call) broke the MCP connection on the second-ever call in a
# long-running process with "RuntimeError: Event loop is closed" -- found
# live, the hard way. This replicates run_sync()'s actual loop-reuse
# pattern, just with a wait_for() wrapped around it for the wall-clock cap.
_EVENT_LOOP = asyncio.new_event_loop()

AGENTS = {
    "boss": boss_agent,
    "inventory": inventory_agent,
    "accounting": accounting_agent,
    "facilities": facilities_agent,
    "customer_service": customer_service_agent,
}

# Live progress for an in-flight run, keyed by ticket_id. `run_ticket()`
# points this at the SAME list object it hands to DelegationDeps.audit, so
# every append a delegated agent makes during the run is visible here
# immediately -- not a simulation, this is the real, in-progress trace.
# Cleared the moment the run ends (success, timeout, or error).
_live_runs: dict[int, list[dict]] = {}


def is_running(ticket_id: int) -> bool:
    return ticket_id in _live_runs


def get_live_steps(ticket_id: int) -> list[dict]:
    return list(_live_runs.get(ticket_id, []))


def _make_delegate_tool(target_name: str):
    """Build one `ask_<target_name>` tool, bound to that specific target
    agent. A factory (rather than one generic function) because each tool
    needs its own name and docstring -- that's what the calling model sees
    when deciding which agent to delegate to."""
    target_agent = AGENTS[target_name]

    async def delegate(ctx: RunContext[DelegationDeps], task: str) -> AgentReply:
        if target_name in ctx.deps.chain:
            raise ModelRetry(
                f"{target_name} is already working on this ticket (chain so far: "
                f"{' -> '.join(ctx.deps.chain)}). Delegating to them again would loop -- "
                "handle this yourself or delegate to a different agent instead."
            )
        if len(ctx.deps.chain) >= MAX_CHAIN_LENGTH:
            raise ModelRetry(
                f"This ticket has already passed through {len(ctx.deps.chain)} agents "
                f"({' -> '.join(ctx.deps.chain)}). Stop delegating further and resolve it yourself."
            )
        # Carries the SAME audit list forward (not a fresh one) so every
        # agent in this ticket's call tree logs into one shared trace.
        sub_deps = DelegationDeps(chain=ctx.deps.chain + (target_name,), audit=ctx.deps.audit)
        try:
            # Deliberately NOT passing usage=ctx.usage here: UsageLimits
            # checks request_limit against the *cumulative* usage object
            # it's given, so sharing one across the whole delegation chain
            # would make AGENT_STEP_LIMIT a single pooled budget split
            # across every agent combined, not 8 steps each (confirmed live:
            # Inventory + Accounting's own correct, efficient steps were
            # silently eating into Boss's own budget, so Boss hit the limit
            # trying to make its final synthesis call even though nothing
            # was actually stuck). Each agent gets its own fresh usage
            # tracker, so its 8-step cap is really its own.
            result = await target_agent.run(task, deps=sub_deps, usage_limits=UsageLimits(request_limit=AGENT_STEP_LIMIT))
        except UsageLimitExceeded:
            timeout_reply = AgentReply(
                message=(
                    f"The {target_name} agent did not complete this within its step limit "
                    f"({AGENT_STEP_LIMIT} steps) -- treat this as a stuck/looping agent, not a real answer."
                ),
                needs_human_approval=False,
                recommended_action=f"Escalate to Boss to investigate why {target_name} could not resolve this efficiently.",
                category="review",
            )
            ctx.deps.audit.append(
                {
                    "agent": target_name,
                    "message": timeout_reply.message,
                    "needs_human_approval": timeout_reply.needs_human_approval,
                    "category": timeout_reply.category,
                    "tool_calls": [],
                    "stop_reason": "step_limit_exceeded",
                }
            )
            return timeout_reply
        ctx.deps.audit.append(
            {
                "agent": target_name,
                "message": result.output.message,
                "needs_human_approval": result.output.needs_human_approval,
                "category": result.output.category,
                "tool_calls": _extract_tool_calls(result.all_messages()),
                "stop_reason": "completed",
            }
        )
        return result.output

    delegate.__name__ = f"ask_{target_name}"
    delegate.__doc__ = (
        f"Delegate a task to the {target_name.replace('_', ' ')} agent and get back their "
        "structured reply: a message, whether it needs human approval, and any recommended "
        "action. Use this instead of guessing about something outside your own role."
    )
    return delegate


for _name, _agent in AGENTS.items():
    for _other_name in AGENTS:
        if _other_name == _name:
            continue
        _agent.tool(_make_delegate_tool(_other_name))


def _plain(value: object) -> object:
    """Convert a tool/delegation result to plain JSON-able data for the
    audit log -- delegation results are AgentReply (a pydantic model), not
    a raw dict."""
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _extract_tool_calls(messages: list[ModelMessage]) -> list[dict]:
    """Pull a flat, readable list of {tool_name, args, result} out of one
    agent run's raw message history, for the audit log."""
    calls: dict[str, dict] = {}
    order: list[str] = []
    for message in messages:
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolCallPart):
                calls[part.tool_call_id] = {"tool_name": part.tool_name, "args": part.args}
                order.append(part.tool_call_id)
            elif isinstance(part, ToolReturnPart) and part.tool_call_id in calls:
                calls[part.tool_call_id]["result"] = _plain(part.content)
            elif isinstance(part, RetryPromptPart) and part.tool_call_id in calls:
                calls[part.tool_call_id]["result"] = f"RETRY: {part.content}"
    return [calls[call_id] for call_id in order]


def _append_audit_entry(entry: dict) -> None:
    """Append-only, never truncated or reset -- the permanent record of
    every ticket run across the life of the project, not a rolling debug
    log (same deliberate choice as Homework 4's audit_trail.json)."""
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if AUDIT_LOG_PATH.exists():
        try:
            entries = json.loads(AUDIT_LOG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            entries = []
    entries.append(entry)
    AUDIT_LOG_PATH.write_text(json.dumps(entries, indent=2, default=str))


def list_tickets() -> list[TicketRecord]:
    """All tickets, each with its real current status -- used by the
    dashboard's ticket list (Problem 7's GET /api/tickets)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    finally:
        conn.close()
    return [TicketRecord(**dict(row)) for row in rows]


def load_ticket(ticket_id: int) -> TicketRecord:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError(f"No ticket with id {ticket_id}")
    return TicketRecord(**dict(row))


def mark_ticket_status(ticket_id: int, status: str) -> None:
    """The only place that writes to tickets.status. Called by run_ticket()
    when the team's work on a ticket is done (see the resolution rule in
    run_ticket's docstring), and by main.py's approve route once a payment
    tied to a ticket actually goes through."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        conn.commit()
    finally:
        conn.close()


def _ticket_task(ticket: TicketRecord) -> str:
    lines = [
        f"Ticket #{ticket.id} ({ticket.type}, status={ticket.status})",
        f"Requester: {ticket.requester}",
        f"Subject: {ticket.subject}",
    ]
    if ticket.sku:
        detail = f"SKU: {ticket.sku}"
        if ticket.size:
            detail += f", size {ticket.size}"
        if ticket.qty:
            detail += f", qty {ticket.qty}"
        lines.append(detail)
    if ticket.lease_id:
        lines.append(f"Lease ID: {ticket.lease_id}")
    if ticket.invoice_id:
        lines.append(f"Invoice ID: {ticket.invoice_id}")
    if ticket.notes:
        lines.append(f"Notes: {ticket.notes}")
    return "\n".join(lines)


def run_ticket(ticket_id: int) -> AgentReply:
    """Hand one open ticket to the Boss agent and return its final reply.
    Boss is the top of the delegation chain -- if even Boss can't resolve a
    ticket within its own step limit, there's no one above it to escalate
    to, so that goes straight to a human instead of a specialist.

    Every run is logged to output/audit_trail.json (Boss's own reply and
    tool/delegation calls, plus every delegated agent's own reply and tool
    calls, in one trace) -- unconditionally, not dependent on a caller
    remembering to check anything.

    Resolution rule (per the student's call): a ticket is marked `resolved`
    as soon as the team is done with it -- UNLESS the final reply is a real
    `category: "payment"` approval request, in which case the ticket stays
    `open` until a human actually approves that payment (main.py's approve
    route is what moves it to `resolved` in that case, once the money
    actually moves). A `category: "review"` approval (Boss stuck, a
    frustrated customer, anything non-monetary) does NOT block resolution --
    the team's work is done either way, a human just also gets looped in
    separately via pending_approvals.json."""
    ticket = load_ticket(ticket_id)
    task = _ticket_task(ticket)
    delegated_calls: list[dict] = []
    _live_runs[ticket_id] = delegated_calls
    start = time.monotonic()
    stop_reason = "completed"
    boss_tool_calls: list[dict] = []
    reply: AgentReply | None = None
    try:
        result = _EVENT_LOOP.run_until_complete(
            asyncio.wait_for(
                boss_agent.run(
                    task,
                    deps=DelegationDeps(chain=("boss",), audit=delegated_calls),
                    usage_limits=UsageLimits(request_limit=AGENT_STEP_LIMIT),
                ),
                timeout=TOTAL_RUN_TIMEOUT_SECONDS,
            )
        )
        boss_tool_calls = _extract_tool_calls(result.all_messages())
        reply = result.output
    except UsageLimitExceeded:
        stop_reason = "step_limit_exceeded"
        reply = AgentReply(
            message=(
                f"Boss did not resolve ticket #{ticket_id} within its step limit "
                f"({AGENT_STEP_LIMIT} steps) -- this needs direct human review."
            ),
            needs_human_approval=True,
            recommended_action="Have a human review this ticket directly; the agent team could not resolve it efficiently.",
            category="review",
        )
    except TimeoutError:
        stop_reason = "timeout"
        reply = AgentReply(
            message=(
                f"Boss did not resolve ticket #{ticket_id} within {TOTAL_RUN_TIMEOUT_SECONDS}s "
                "-- this needs direct human review."
            ),
            needs_human_approval=True,
            recommended_action="Have a human review this ticket directly; the agent team took too long to resolve it.",
            category="review",
        )
    except Exception:
        stop_reason = "error"
        raise
    finally:
        _live_runs.pop(ticket_id, None)
        duration_ms = int((time.monotonic() - start) * 1000)
        _append_audit_entry(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ticket_id": ticket_id,
                "boss_reply": {
                    "message": reply.message,
                    "needs_human_approval": reply.needs_human_approval,
                    "category": reply.category,
                }
                if reply is not None
                else None,
                "boss_tool_calls": boss_tool_calls,
                "delegated_agent_calls": delegated_calls,
                "stop_reason": stop_reason,
                "duration_ms": duration_ms,
            }
        )

    is_pending_payment = reply.needs_human_approval and reply.category == "payment"
    if reply.needs_human_approval:
        record_pending_approval(
            ticket_id,
            reply.message,
            reply.recommended_action,
            category=reply.category,
            payment_amount=reply.payment_amount,
            payment_account=reply.payment_account,
        )
    mark_ticket_status(ticket_id, "open" if is_pending_payment else "resolved")
    return reply
