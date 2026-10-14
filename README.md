# Campus Customs — Multi-Agent Operations

Homework 5 for MGT409 (AI Foundations for Managers): a FastMCP tool server, a 5-agent PydanticAI team (Boss, Inventory, Accounting, Facilities, Customer Service), a FastAPI backend, and a React dashboard for running Campus Customs' desk tickets end to end. Every agent runs on `gpt-6-luna` via Portkey. Full design history and decisions are in `output/harness.md`; every prompt used to build this is logged verbatim in `AI_prompts.md`.

## Setup

1. **Clone the repo and `cd` into it.**

2. **Python dependencies** (Python 3.11+):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Frontend dependencies:**
   ```bash
   npm install --prefix frontend
   ```

4. **API key**: copy `.env.example` to `.env` in the project root and fill in a real Portkey API key. `backend/runtime.py` loads this automatically. Never commit the real `.env` (it's gitignored).
   ```bash
   cp .env.example .env
   ```

5. **Working database copy** — before the very first run, make the mutable working copy from the untouched original seed:
   ```bash
   cp data/campus_customs.db data/campus_customs_new.db
   ```
   `data/campus_customs.db` is the original seed and is never written to by anything in this project. `data/campus_customs_new.db` is the only database every tool and agent actually reads/writes.

## Running it

All commands below assume your shell's current directory is the **project root** (where this README and `.mcp.json` live) — `.mcp.json` uses a path relative to the root (`mcp_server/server.py`), so the backend needs to be launched from here for it to find the MCP server.

**1. MCP server** — in normal use this is launched automatically (over stdio) by whatever connects to it, per `.mcp.json`: Claude Code's own session, or the backend's `load_mcp_toolsets()` call in `backend/runtime.py`. You don't need to start it by hand. To run it standalone (e.g. to smoke-test a tool call directly):
```bash
python3 mcp_server/server.py
```

**2. FastAPI backend** (the agent team + all API routes):
```bash
python3 -m uvicorn main:app --reload --port 8000 --app-dir backend
```
This is the first thing that actually calls the live Portkey API — nothing before this point does.

**3. React dashboard:**
```bash
npm run dev --prefix frontend
```
Open the URL Vite prints (default `http://localhost:5173`). The dashboard talks to the backend at `http://localhost:8000`.

**4. Reset the desk before a full three-ticket run.** Click "Reset Desk" in the dashboard header, or:
```bash
curl -X POST http://localhost:8000/api/reset
```
This archives the current working database and any pending approvals into `output/archive/reset_<timestamp>/` (never deletes them), rebuilds a fresh working copy from `data/campus_customs.db`, and appends one marker entry to `output/audit_trail.json` (which is otherwise permanent and never cleared). After resetting, all 3 tickets (101, 102, 103) are back to `open` and checking is back to its seed balance.

## Project layout

```
.
├── AI_prompts.md          every prompt used to build this, verbatim, problem by problem
├── requirements.txt
├── .env.example
├── .mcp.json              MCP server registration (stdio, relative paths)
├── data/
│   ├── campus_customs.db       original seed, never modified
│   └── campus_customs_new.db   working copy, mutated by agent runs and resets
├── mcp_server/
│   ├── server.py          FastMCP server, 6 read-only tools over the working db
│   └── README.md
├── backend/
│   ├── main.py            FastAPI app, all API routes
│   ├── models.py          shared AgentReply / TicketRecord types
│   ├── runtime.py, team.py, delegation.py, approvals.py, payments.py, reset_db.py
│   └── prompts/           the 5 agents' system prompts (boss, inventory, accounting, facilities, customer_service)
├── frontend/               React + Vite + TypeScript dashboard
└── output/
    ├── harness.md          full build log and design decisions
    ├── mcp_smoke.json       Problem 3/4 smoke-test evidence
    ├── desk_tickets.html    Expected / Actual / Cash / Reflection — double-click to open
    ├── design.md            dashboard creative-direction history
    ├── resolved_tickets.json
    ├── resolved_board.html  real dashboard screenshots per resolved ticket — double-click to open
    ├── audit_trail.json     permanent, append-only log of every real agent run
    └── github_url.txt
```

## Safety notes

- All 6 MCP tools are read-only lookups. The only function in the whole system that writes anything is `backend/payments.py`'s `apply_payment()`, and it's only ever called after a human has explicitly approved a payment (or confirmed a payment's status) through the dashboard — never by an agent directly.
- Every agent is structurally restricted to its own domain's tool(s) (`backend/runtime.py`'s `mcp_tools_for()`) — this isn't just a prompt instruction, the tool is literally not visible to an agent outside its lane.
- See `output/harness.md`'s "Safety" section for the full list of guardrails (approval gating, delegation-loop prevention, step/time limits, full audit trail).
