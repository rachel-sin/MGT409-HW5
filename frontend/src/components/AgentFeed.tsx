import type { AgentEvent } from "../types";
import { agentColor, agentLabel, MODEL_NAME } from "../agentMeta";

interface Props {
  events: AgentEvent[];
  visibleCount: number;
  emptyMessage?: string;
}

export function AgentFeed({ events, visibleCount, emptyMessage }: Props) {
  if (events.length === 0) {
    return (
      <div style={{ color: "#555", fontStyle: "italic", padding: "1rem 0" }}>
        {emptyMessage ?? '(nothing yet... click "run agents" to wake the team up!!)'}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
      {events.slice(0, visibleCount).map((event, i) => (
        <div
          key={i}
          className="retro-panel"
          style={{
            border: `3px dashed ${agentColor(event.agent)}`,
            boxShadow: `5px 5px 0 ${agentColor(event.agent)}`,
            padding: "0.75rem 1rem",
            animation: "fadeIn 220ms ease",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "0.35rem",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: "0.45rem", flexWrap: "wrap" }}>
              <span style={{ fontWeight: 700, color: agentColor(event.agent), fontSize: "0.95rem" }}>
                🤖 {agentLabel(event.agent)} says:
              </span>
              <span
                style={{
                  fontSize: "0.65rem",
                  color: "#888",
                  border: "1px dashed #bbb",
                  borderRadius: 4,
                  padding: "0.05rem 0.4rem",
                  fontFamily: "monospace",
                }}
                title="Every agent in this system runs on the same model."
              >
                {MODEL_NAME}
              </span>
            </span>
            {event.tool_calls.length > 0 && (
              <span
                style={{
                  fontSize: "0.7rem",
                  color: "#fff",
                  background: agentColor(event.agent),
                  padding: "0.1rem 0.5rem",
                  borderRadius: 4,
                  fontFamily: "monospace",
                }}
              >
                ⚙ {event.tool_calls.map((tc) => tc.tool_name).join(", ")}
              </span>
            )}
          </div>
          <div style={{ fontSize: "0.92rem" }}>{event.message}</div>
          {event.needs_human_approval && (
            <div
              className="rainbow-text"
              style={{
                marginTop: "0.5rem",
                display: "inline-block",
                fontSize: "0.8rem",
              }}
            >
              {event.category === "payment" ? "!!! needs $$$ approval !!!" : "!!! needs a human !!!"}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
