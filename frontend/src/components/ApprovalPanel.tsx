import type { PendingApproval } from "../types";

interface Props {
  approval: PendingApproval;
  onApprove: () => void;
  approving: boolean;
  onConfirmPaymentStatus: (alreadyPaid: boolean) => void;
  confirmingPaymentStatus: boolean;
}

const money = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });

export function ApprovalPanel({
  approval,
  onApprove,
  approving,
  onConfirmPaymentStatus,
  confirmingPaymentStatus,
}: Props) {
  if (approval.status !== "pending") {
    // For a payment-status check, "rejected" doesn't mean the request was
    // turned down -- decide(approved=false) is reused here to mean "already
    // paid, nothing more to do," so it needs its own label rather than
    // reading like a rejection.
    const settledLabel =
      approval.category === "payment_pending_confirmation" && approval.status === "rejected"
        ? "ALREADY PAID -- NO DUPLICATE SENT"
        : approval.status === "approved"
          ? "APPROVED"
          : "REJECTED";
    return (
      <div
        className="retro-panel"
        style={{
          border: "3px dashed var(--sage)",
          boxShadow: "5px 5px 0 var(--sage)",
          padding: "0.9rem 1.1rem",
          marginTop: "1rem",
          color: "var(--sage)",
          fontSize: "0.9rem",
          fontWeight: 700,
        }}
      >
        ✓✓✓ {settledLabel} by {approval.decided_by} on{" "}
        {approval.decided_at ? new Date(approval.decided_at).toLocaleString() : ""} ✓✓✓
      </div>
    );
  }

  if (approval.category === "payment_pending_confirmation") {
    return (
      <div
        className="retro-panel"
        style={{
          border: "3px dashed var(--hot)",
          boxShadow: "5px 5px 0 var(--hot)",
          padding: "1rem 1.1rem",
          marginTop: "1rem",
        }}
      >
        <div className="rainbow-text" style={{ fontSize: "1.1rem", marginBottom: "0.4rem" }}>
          ⚠ has this already been paid? ⚠
        </div>
        <div style={{ fontSize: "0.92rem", marginBottom: "0.5rem" }}>{approval.recommended_action}</div>
        {approval.payment_amount != null && (
          <div
            style={{
              fontFamily: "monospace",
              fontSize: "1.4rem",
              marginBottom: "0.75rem",
              color: "var(--yale)",
              fontWeight: 700,
            }}
          >
            {money(approval.payment_amount)}{" "}
            <span style={{ fontSize: "0.8rem", color: "#555", fontFamily: "inherit" }}>
              from {approval.payment_account}
            </span>
          </div>
        )}
        <div style={{ display: "flex", gap: "0.6rem" }}>
          <button
            onClick={() => onConfirmPaymentStatus(false)}
            disabled={confirmingPaymentStatus}
            className="retro-btn"
            style={{ padding: "0.6rem 1.1rem" }}
          >
            {confirmingPaymentStatus ? "working..." : "✘ no, pay it ✘"}
          </button>
          <button
            onClick={() => onConfirmPaymentStatus(true)}
            disabled={confirmingPaymentStatus}
            className="retro-btn"
            style={{ padding: "0.6rem 1.1rem" }}
          >
            {confirmingPaymentStatus ? "working..." : "✔ yes, already paid ✔"}
          </button>
        </div>
      </div>
    );
  }

  // Only a real "payment" approval can actually be approved through this
  // panel -- the backend's approve route only ever acts on category ==
  // "payment" (it has a real amount/account to move); a "review" flag
  // (Boss stuck, a frustrated customer, anything non-monetary) has nothing
  // for that route to do, so showing an "approve" button for it would just
  // lead to a confusing failed request.
  if (approval.category !== "payment") {
    return (
      <div
        className="retro-panel"
        style={{
          border: "3px dashed var(--amber)",
          boxShadow: "5px 5px 0 var(--amber)",
          padding: "1rem 1.1rem",
          marginTop: "1rem",
        }}
      >
        <div className="rainbow-text" style={{ fontSize: "1.1rem", marginBottom: "0.4rem" }}>
          🚩 flagged for human review (no $$$ involved)
        </div>
        <div style={{ fontSize: "0.92rem" }}>{approval.recommended_action ?? approval.message}</div>
      </div>
    );
  }

  return (
    <div
      className="retro-panel"
      style={{
        border: "3px dashed var(--hot)",
        boxShadow: "5px 5px 0 var(--hot)",
        padding: "1rem 1.1rem",
        marginTop: "1rem",
      }}
    >
      <div className="rainbow-text" style={{ fontSize: "1.1rem", marginBottom: "0.4rem" }}>
        ⚠ needs YOUR approval — real $$$ ⚠
      </div>
      <div style={{ fontSize: "0.92rem", marginBottom: "0.5rem" }}>{approval.recommended_action}</div>
      {approval.payment_amount != null && (
        <div
          style={{
            fontFamily: "monospace",
            fontSize: "1.4rem",
            marginBottom: "0.75rem",
            color: "var(--yale)",
            fontWeight: 700,
          }}
        >
          {money(approval.payment_amount)}{" "}
          <span style={{ fontSize: "0.8rem", color: "#555", fontFamily: "inherit" }}>
            from {approval.payment_account}
          </span>
        </div>
      )}
      <button onClick={onApprove} disabled={approving} className="retro-btn" style={{ padding: "0.6rem 1.3rem" }}>
        {approving ? "approving..." : "✔ approve payment ✔"}
      </button>
    </div>
  );
}
