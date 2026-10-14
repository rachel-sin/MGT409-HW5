import type { Ticket } from "../types";

const TYPE_LABELS: Record<string, string> = {
  customer_order: "Customer Order",
  rent_notice: "Rent Notice",
  price_override: "Price Override",
};

interface Props {
  ticket: Ticket;
  selected: boolean;
  onSelect: () => void;
}

export function TicketCard({ ticket, selected, onSelect }: Props) {
  return (
    <button
      onClick={onSelect}
      className="retro-panel"
      style={{
        display: "block",
        width: "100%",
        textAlign: "left",
        border: selected ? "4px dashed var(--hot)" : "4px dashed var(--yale)",
        boxShadow: selected ? "7px 7px 0 var(--hot)" : "7px 7px 0 var(--yale)",
        padding: "0.9rem 1rem",
        marginBottom: "1.1rem",
        cursor: "pointer",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: "0.75rem", color: "var(--yale)", marginBottom: "0.2rem", fontWeight: 700 }}>
            📌 #{ticket.id} &middot; {TYPE_LABELS[ticket.type] ?? ticket.type}
          </div>
          <h3 style={{ fontSize: "1.05rem" }}>{ticket.subject}</h3>
        </div>
        <span className={ticket.status === "resolved" ? "badge badge-resolved" : "badge badge-open"}>
          {ticket.status === "resolved" ? "✓ done" : "open!!"}
        </span>
      </div>
      <div style={{ fontSize: "0.85rem", color: "#555", marginTop: "0.5rem" }}>from: {ticket.requester}</div>
    </button>
  );
}
