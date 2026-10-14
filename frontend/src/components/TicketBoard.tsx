import type { Ticket } from "../types";
import { TicketCard } from "./TicketCard";

interface Props {
  tickets: Ticket[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

export function TicketBoard({ tickets, selectedId, onSelect }: Props) {
  return (
    <div>
      <h2 className="rainbow-text" style={{ fontSize: "1.2rem", marginBottom: "0.9rem" }}>
        ☆ open tickets ☆
      </h2>
      {tickets.map((t) => (
        <TicketCard key={t.id} ticket={t} selected={t.id === selectedId} onSelect={() => onSelect(t.id)} />
      ))}
    </div>
  );
}
