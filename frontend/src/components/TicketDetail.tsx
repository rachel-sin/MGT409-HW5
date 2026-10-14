import { useEffect, useState } from "react";
import { getLiveRun } from "../api";
import type { AgentEvent, PendingApproval, Ticket } from "../types";
import { PLAIN_ENGLISH_QUESTION } from "../agentMeta";
import { AgentFeed } from "./AgentFeed";
import { ApprovalPanel } from "./ApprovalPanel";

export type RunPhase = "idle" | "loading" | "revealing" | "done";

interface Props {
  ticket: Ticket;
  events: AgentEvent[];
  pendingApproval: PendingApproval | null;
  onRun: () => void;
  onRevealFinished: () => void;
  onApprove: () => void;
  phase: RunPhase;
  approving: boolean;
  onConfirmPaymentStatus: (alreadyPaid: boolean) => void;
  confirmingPaymentStatus: boolean;
}

export function TicketDetail({
  ticket,
  events,
  pendingApproval,
  onRun,
  onRevealFinished,
  onApprove,
  phase,
  approving,
  onConfirmPaymentStatus,
  confirmingPaymentStatus,
}: Props) {
  const [visibleCount, setVisibleCount] = useState(phase === "done" ? events.length : 0);
  const [liveEvents, setLiveEvents] = useState<AgentEvent[]>([]);
  const [elapsedSec, setElapsedSec] = useState(0);

  // While waiting on the real backend call, poll its genuine in-progress
  // trace (not simulated) so the feed fills in live as each delegated
  // agent actually finishes its step. Boss's own reasoning only shows up
  // once the whole run completes -- it's one blocking call underneath.
  useEffect(() => {
    if (phase !== "loading") {
      setLiveEvents([]);
      setElapsedSec(0);
      return;
    }
    let cancelled = false;
    const poll = setInterval(async () => {
      try {
        const status = await getLiveRun(ticket.id);
        if (cancelled) return;
        setLiveEvents(
          status.steps.map((s) => ({
            ticket_id: ticket.id,
            agent: s.agent,
            message: s.message,
            needs_human_approval: null,
            category: null,
            tool_calls: s.tool_calls.map((tc) => ({ tool_name: tc.tool_name, args: {} })),
            timestamp: "",
          })),
        );
      } catch {
        // Polling failure isn't worth surfacing -- the main run request
        // will report its own error when it finishes.
      }
    }, 1000);
    const clock = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    return () => {
      cancelled = true;
      clearInterval(poll);
      clearInterval(clock);
    };
  }, [phase, ticket.id]);

  useEffect(() => {
    if (phase !== "revealing") {
      if (phase === "done") setVisibleCount(events.length);
      return;
    }
    setVisibleCount(0);
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setVisibleCount(i);
      if (i >= events.length) {
        clearInterval(id);
        onRevealFinished();
      }
    }, 650);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, ticket.id]);

  const started = phase !== "idle";
  // Boss's final message IS the direct answer to the plain-English
  // question -- it was always in the feed, just buried as "one more
  // message bubble" rather than surfaced as the answer.
  const bossAnswer = phase === "done" ? events.find((e) => e.agent === "boss")?.message : null;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
        <div>
          <div style={{ fontSize: "0.8rem", color: "var(--yale)", fontWeight: 700 }}>ticket #{ticket.id}</div>
          <h2 className="glow-title" style={{ fontSize: "1.7rem" }}>
            {ticket.subject}
          </h2>
        </div>
        <span className={ticket.status === "resolved" ? "badge badge-resolved" : "badge badge-open"}>
          {ticket.status === "resolved" ? "✓ done!!" : "open!!"}
        </span>
      </div>

      <div
        className="retro-panel"
        style={{
          border: "3px dotted var(--gold-dark)",
          boxShadow: "none",
          padding: "0.9rem 1.1rem",
          fontSize: "0.92rem",
          marginBottom: "1.25rem",
        }}
      >
        <strong>✦ in plain english: ✦</strong> {PLAIN_ENGLISH_QUESTION[ticket.id]}
      </div>

      {bossAnswer && (
        <div
          className="retro-panel"
          style={{
            border: "3px dashed var(--sage)",
            boxShadow: "5px 5px 0 var(--sage)",
            padding: "0.9rem 1.1rem",
            marginBottom: "1.25rem",
          }}
        >
          <div style={{ fontWeight: 700, color: "var(--sage)", marginBottom: "0.35rem" }}>✅ the answer:</div>
          <div style={{ fontSize: "0.95rem" }}>{bossAnswer}</div>
        </div>
      )}

      {!started && (
        <button onClick={onRun} className="retro-btn" style={{ padding: "0.75rem 1.5rem", fontSize: "1rem", marginBottom: "1.25rem" }}>
          ☆彡 run agents 彡☆
        </button>
      )}

      {phase === "loading" && (
        <>
          <div className="rainbow-text" style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>
            ⏳ agents are thinking... ({elapsedSec}s elapsed — real AI calls, Boss's own answer only appears once
            everything below is done)
          </div>
          <AgentFeed events={liveEvents} visibleCount={liveEvents.length} emptyMessage="(waking up Boss...)" />
        </>
      )}

      {(phase === "revealing" || phase === "done") && (
        <>
          <h3 className="rainbow-text" style={{ fontSize: "1rem", marginBottom: "0.6rem" }}>
            {phase === "revealing" ? "⚡ agents at work... ⚡" : "✉ agent guestbook ✉"}
          </h3>
          <AgentFeed events={events} visibleCount={visibleCount} />

          {phase === "done" && pendingApproval && (
            <ApprovalPanel
              approval={pendingApproval}
              onApprove={onApprove}
              approving={approving}
              onConfirmPaymentStatus={onConfirmPaymentStatus}
              confirmingPaymentStatus={confirmingPaymentStatus}
            />
          )}

          {phase === "done" && (
            <button
              onClick={onRun}
              className="retro-btn"
              style={{ padding: "0.6rem 1.2rem", fontSize: "0.85rem", marginTop: "1.25rem" }}
            >
              🔁 run agents again
            </button>
          )}
        </>
      )}
    </div>
  );
}
