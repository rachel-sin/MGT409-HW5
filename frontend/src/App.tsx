import { useEffect, useState } from "react";
import {
  approvePayment,
  confirmPaymentStatus,
  getApprovals,
  getCash,
  getEvents,
  getTickets,
  latestRunEvents,
  resetDesk,
  runTicket,
  sinceLastReset,
} from "./api";
import { CashHeader } from "./components/CashHeader";
import { TicketBoard } from "./components/TicketBoard";
import { TicketDetail, type RunPhase } from "./components/TicketDetail";
import type { AgentEvent, CashBalance, PendingApproval, Ticket } from "./types";

function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [phaseByTicket, setPhaseByTicket] = useState<Record<number, RunPhase>>({});
  const [eventsByTicket, setEventsByTicket] = useState<Record<number, AgentEvent[]>>({});
  const [approvalsByTicket, setApprovalsByTicket] = useState<Record<number, PendingApproval | null>>({});
  const [approvingId, setApprovingId] = useState<number | null>(null);
  const [confirmingPaymentStatusId, setConfirmingPaymentStatusId] = useState<number | null>(null);
  const [cash, setCash] = useState<CashBalance | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    try {
      const [freshTickets, freshCash, pending, allEvents] = await Promise.all([
        getTickets(),
        getCash(),
        getApprovals(),
        getEvents(300),
      ]);
      setTickets(freshTickets);
      setCash(freshCash);
      const byTicket: Record<number, PendingApproval | null> = {};
      for (const a of pending) byTicket[a.ticket_id] = a;
      setApprovalsByTicket(byTicket);

      // Restore past runs from the backend's real record -- a page reload
      // (or clicking away and back) should never discard what the agents
      // already did. The audit trail is the actual source of truth, not
      // whatever happens to still be in this tab's memory.
      const restoredEvents: Record<number, AgentEvent[]> = {};
      const restoredPhase: Record<number, RunPhase> = {};
      const eventsSinceReset = sinceLastReset(allEvents);
      for (const ticket of freshTickets) {
        const previousRun = latestRunEvents(eventsSinceReset, ticket.id);
        if (previousRun.length > 0) {
          restoredEvents[ticket.id] = previousRun;
          restoredPhase[ticket.id] = "done";
        }
      }
      setEventsByTicket((prev) => ({ ...restoredEvents, ...prev }));
      setPhaseByTicket((prev) => ({ ...restoredPhase, ...prev }));

      setSelectedId((prev) => prev ?? freshTickets[0]?.id ?? null);
      setError(null);
    } catch {
      setError("Can't reach the backend at localhost:8000 — is `uvicorn main:app --reload --port 8000` running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  const selectedTicket = tickets.find((t) => t.id === selectedId) ?? null;
  const events = selectedId != null ? (eventsByTicket[selectedId] ?? []) : [];
  const phase = selectedId != null ? (phaseByTicket[selectedId] ?? "idle") : "idle";
  const pendingApproval = selectedId != null ? (approvalsByTicket[selectedId] ?? null) : null;

  async function handleRun() {
    if (selectedId == null) return;
    const id = selectedId;
    setPhaseByTicket((prev) => ({ ...prev, [id]: "loading" }));
    try {
      await runTicket(id);
      const [allEvents, freshTickets, approvals, freshCash] = await Promise.all([
        getEvents(50),
        getTickets(),
        getApprovals(id),
        getCash(),
      ]);
      setEventsByTicket((prev) => ({ ...prev, [id]: latestRunEvents(allEvents, id) }));
      setTickets(freshTickets);
      setApprovalsByTicket((prev) => ({ ...prev, [id]: approvals[0] ?? null }));
      setCash(freshCash);
      setPhaseByTicket((prev) => ({ ...prev, [id]: "revealing" }));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong running this ticket.");
      setPhaseByTicket((prev) => ({ ...prev, [id]: "idle" }));
    }
  }

  function handleRevealFinished() {
    if (selectedId == null) return;
    setPhaseByTicket((prev) => ({ ...prev, [selectedId]: "done" }));
  }

  async function handleApprove() {
    if (!pendingApproval || selectedId == null) return;
    setApprovingId(pendingApproval.id);
    try {
      await approvePayment(pendingApproval.id, "rachel.sin@yale.edu");
      const [freshTickets, approvals, freshCash] = await Promise.all([
        getTickets(),
        getApprovals(selectedId),
        getCash(),
      ]);
      setTickets(freshTickets);
      setApprovalsByTicket((prev) => ({ ...prev, [selectedId]: approvals[0] ?? null }));
      setCash(freshCash);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't approve that payment.");
    } finally {
      setApprovingId(null);
    }
  }

  async function handleConfirmPaymentStatus(alreadyPaid: boolean) {
    if (!pendingApproval || selectedId == null) return;
    setConfirmingPaymentStatusId(pendingApproval.id);
    try {
      await confirmPaymentStatus(pendingApproval.id, alreadyPaid, "rachel.sin@yale.edu");
      const [freshTickets, approvals, freshCash] = await Promise.all([
        getTickets(),
        getApprovals(selectedId),
        getCash(),
      ]);
      setTickets(freshTickets);
      setApprovalsByTicket((prev) => ({ ...prev, [selectedId]: approvals[0] ?? null }));
      setCash(freshCash);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't confirm payment status.");
    } finally {
      setConfirmingPaymentStatusId(null);
    }
  }

  async function handleReset() {
    try {
      await resetDesk();
      setPhaseByTicket({});
      setEventsByTicket({});
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't reset the desk.");
    }
  }

  // A little 2002-internet cursor sparkle trail, because why not.
  useEffect(() => {
    const SPARKLES = ["✦", "★", "✧", "☆"];
    function onMove(e: MouseEvent) {
      if (Math.random() > 0.35) return; // thin out the trail
      const el = document.createElement("span");
      el.className = "sparkle";
      el.textContent = SPARKLES[Math.floor(Math.random() * SPARKLES.length)];
      el.style.left = `${e.clientX + (Math.random() * 10 - 5)}px`;
      el.style.top = `${e.clientY + (Math.random() * 10 - 5)}px`;
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 700);
    }
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  return (
    <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" }}>
      <CashHeader cash={cash ?? { name: "checking", balance: 0, date: "" }} onReset={handleReset} />

      {error && (
        <div
          className="retro-panel"
          style={{
            margin: "0 auto 1rem",
            maxWidth: 700,
            border: "3px dashed var(--dusty-red)",
            boxShadow: "5px 5px 0 var(--dusty-red)",
            padding: "0.75rem 1rem",
            color: "var(--dusty-red)",
            fontWeight: 700,
            textAlign: "center",
          }}
        >
          ⚠ {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", color: "var(--gold)", padding: "3rem" }}>loading the desk...</div>
      ) : (
        <div style={{ display: "flex", flex: 1, gap: "2rem", padding: "1.75rem", maxWidth: 1100, margin: "0 auto", width: "100%" }}>
          <div style={{ width: 300, flexShrink: 0 }}>
            <TicketBoard tickets={tickets} selectedId={selectedId} onSelect={setSelectedId} />
          </div>
          {selectedTicket && (
            <div className="retro-panel" style={{ flex: 1, padding: "1.75rem" }}>
              <TicketDetail
                ticket={selectedTicket}
                events={events}
                pendingApproval={pendingApproval}
                onRun={handleRun}
                onRevealFinished={handleRevealFinished}
                onApprove={handleApprove}
                phase={phase}
                approving={approvingId === pendingApproval?.id}
                onConfirmPaymentStatus={handleConfirmPaymentStatus}
                confirmingPaymentStatus={confirmingPaymentStatusId === pendingApproval?.id}
              />
            </div>
          )}
        </div>
      )}

      <footer style={{ textAlign: "center", color: "var(--gold)", fontSize: "0.8rem", padding: "1.5rem 1rem 2rem" }}>
        <hr className="retro-divider" style={{ maxWidth: 500, margin: "0 auto 1rem" }} />
        ⚠ best viewed in Netscape Navigator 6.0 @ 1024x768 ⚠<br />
        page last updated: {new Date().toLocaleDateString()} ✦ made with lots of ✨ by the Campus Customs team
      </footer>
    </div>
  );
}

export default App;
