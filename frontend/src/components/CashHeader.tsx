import { MODEL_NAME, MODEL_PROVIDER } from "../agentMeta";
import type { CashBalance } from "../types";

interface Props {
  cash: CashBalance;
  onReset: () => void;
}

const money = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });

export function CashHeader({ cash, onReset }: Props) {
  return (
    <>
      <marquee>
        ✧･ﾟ: *✧･ﾟ:* WELCOME TO THE CAMPUS CUSTOMS DESK *:･ﾟ✧*:･ﾟ✧ now hiring AI agents 4 u!! click a ticket 2 begin
        ~*~ best viewed @ 1024x768 ~*~ no refunds lol ~*~
      </marquee>

      <header style={{ textAlign: "center", padding: "1.1rem 1rem 0.6rem" }}>
        <h1 className="glow-title" style={{ fontSize: "2.6rem" }}>
          ~*✧･ﾟ YALE ･ﾟ✧*~
        </h1>
        <div style={{ color: "var(--gold)", fontWeight: 700, fontSize: "1rem" }}>
          <span className="rainbow-text">Campus Customs Desk</span> :: agent ops HQ :: xoxo
        </div>
        <div style={{ marginTop: "0.35rem" }}>
          <span
            style={{
              display: "inline-block",
              background: "rgba(255,214,10,0.15)",
              border: "1px dashed var(--gold)",
              color: "var(--gold)",
              borderRadius: 6,
              padding: "0.15rem 0.6rem",
              fontSize: "0.72rem",
              fontWeight: 700,
            }}
          >
            🧠 every agent runs on {MODEL_NAME} via {MODEL_PROVIDER}
          </span>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: "1rem",
            marginTop: "1rem",
            flexWrap: "wrap",
          }}
        >
          <div
            className="retro-panel"
            style={{ padding: "0.5rem 1rem", display: "inline-flex", alignItems: "center", gap: "0.6rem" }}
          >
            <span style={{ fontSize: "0.85rem", fontWeight: 700 }}>💰 CHECKING:</span>
            <span style={{ fontFamily: "monospace", fontSize: "1.1rem", color: "var(--yale)", fontWeight: 700 }}>
              {money(cash.balance)}
            </span>
          </div>

          <div
            style={{
              background: "#000",
              color: "#39ff14",
              fontFamily: "monospace",
              fontWeight: 700,
              padding: "0.5rem 0.9rem",
              borderRadius: 4,
              border: "3px dashed var(--gold)",
              letterSpacing: "0.1em",
            }}
          >
            👁️ VISITORS: 001337
          </div>

          <button onClick={onReset} className="retro-btn" style={{ padding: "0.5rem 1rem" }}>
            🔄 reset desk
          </button>
        </div>
      </header>
    </>
  );
}
