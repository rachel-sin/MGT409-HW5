# Harness — Homework 5

This file documents the Campus Customs Multi-Agent Operations build as it grows across problems: the database, tools, agent behavior, and guardrails. It will be updated in every later problem.

## Database

`data/campus_customs.db` is the original seed database — kept untouched as a reference. All agent/tool work reads and writes `data/campus_customs_new.db`, a working copy made in Problem 2 (`cp data/campus_customs.db data/campus_customs_new.db`).

### tickets

- `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`

Why it matters: this is the shared work queue — every ticket is something the shop needs handled, and the Boss agent reads this table first to decide which agent(s) a ticket should go to.

### inventory

- `sku`, `name`, `size`, `qty`, `location` (primary key: `sku` + `size`)

Why it matters: the Inventory agent's source of truth for stock on hand per SKU/size, used to spot shortfalls and confirm whether a customer order or bulk request can actually be fulfilled.

### pricing

- `sku`, `unit_cost`, `list_price`

Why it matters: lets the Accounting agent compute margin and evaluate whether a discount request (like a price-override ticket) still leaves a healthy margin.

### vendors

- `id`, `name`, `specialty`, `lead_days`

Why it matters: tells the Inventory agent who can restock a given SKU and how long it will take, which matters when deciding how urgently to act on a shortfall.

### invoices

- `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`

Why it matters: tracks money the shop owes vendors; the Accounting agent uses this to prepare payments and flag anything overdue.

### payments

- `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`

Why it matters: the paid-out record (rent, invoices, etc.) — Accounting checks this before assuming something is still owed, and every payment needs a human (`approved_by`) behind it.

### leases

- `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`

Why it matters: the Facilities agent's reference for shop space obligations — rent amount and when it's next due.

### cash_accounts

- `name`, `balance`, `date`

Why it matters: tells Accounting how much cash is actually on hand before approving a payment or purchase order.

### desk

- `date_today`, `notes`

Why it matters: a single-row table giving the agents "today's date" so due dates (rent, invoices) can be judged as upcoming, due, or overdue.

## The 3 Open Tickets (Problem 2 walkthrough)

**Ticket 101 — `customer_order`** (Tauhid Zaman wants `CC-TEE-WHITE`, size S, qty 1)
- `inventory`: `CC-TEE-WHITE` / S is at **0 qty** — the shop can't fulfill this from stock right now.
- `invoice_id = 501` → `invoices`: a $840 invoice from vendor 1, described as "Rush reprint CC-TEE-WHITE S," due 2026-08-28 and still `open`.
- `vendor_id = 1` → `vendors`: Bulldog Print Co, specialty "apparel reprint," 5-day lead time — the vendor already rush-printing the exact SKU/size that's out of stock.
- `pricing`: `CC-TEE-WHITE` costs $8, lists for $28.
- Story: this customer's size is out of stock, but a reprint is already in motion (and its invoice is overdue) — Inventory and Accounting both have a stake in this one ticket.

**Ticket 102 — `rent_notice`** (Elm City Properties: rent due in 2 days)
- `lease_id = 1` → `leases`: Chapel Street shop, landlord Elm City Properties, $2,400/month, next due 2026-09-02.
- `desk.date_today = 2026-08-31` — confirms "due in 2 days" is accurate.
- `cash_accounts`: checking balance is $3,400 — enough to cover the $2,400 rent.
- `payments`: 0 rows — nothing has been paid yet this cycle, so this is still fully outstanding.
- Story: a straightforward Facilities/Accounting ticket — rent is due soon, and there's cash on hand to cover it, but no payment has been logged.

**Ticket 103 — `price_override`** (Yale AI Club wants 20x `CC-HOOD-NAVY`, size M, bulk discount)
- `inventory`: `CC-HOOD-NAVY` / M is at only **8 qty** — a shortfall of 12 against the requested 20.
- `pricing`: `CC-HOOD-NAVY` costs $22, lists for $58 (big margin to work with when considering a discount).
- No `lease_id`/`invoice_id` — this ticket doesn't touch leases or invoices.
- Story: Inventory needs to flag the stock shortfall (and possibly loop in a vendor to restock) before Accounting can evaluate whether a bulk discount still makes sense on the 8 units actually available.

## MCP Tools (Problem 3)

`mcp_server/server.py` — a FastMCP server over `data/campus_customs_new.db`. Built but not connected or run yet (per instruction). See `mcp_server/README.md` for the server overview.

| Tool | Table read | Ticket it unlocks | Why this tool is right for that ticket |
|------|-----------|--------------------|------------------------------------------|
| `get_inventory_level(sku, size)` | `inventory` | **103** — Yale AI Club's 20x bulk hoodie request | The ticket's ask (20 units, size M) can't be evaluated at all until someone checks real stock; this tool returns the true 8-on-hand number, surfacing the 12-unit shortfall instead of letting an agent assume the order is fulfillable. |
| `get_lease_details(lease_id)` | `leases` | **102** — the rent-due notice | The ticket's own `notes` field ("rent due in 2 days") never states the actual rent amount; this tool follows the ticket's `lease_id` straight to the real $2,400 figure and the 2026-09-02 due date, which is the one fact needed before anyone can act on the notice. |
| `get_invoice_details(invoice_id)` | `invoices` | **101** — Tauhid Zaman's out-of-stock tee order | The ticket's own `invoice_id` (501) points directly at this row; the tool confirms the $840 reprint invoice is real, already overdue, and specifically for "CC-TEE-WHITE S" — telling the agent a fix for this exact stockout is already in motion rather than something to invent or promise blindly. |

### Why these 3 (and not the others)

Each tool is the shortest, most direct path from a ticket's own fields to the single fact that actually unblocks it — `get_inventory_level` resolves the blocking question first (can this even be filled), `get_lease_details` follows the ticket's `lease_id` one hop to the missing rent figure, and `get_invoice_details` follows the ticket's `invoice_id` one hop to confirm a fix is already underway. Tools considered but not built this round: `get_pricing(sku)`, `get_cash_balance(account_name)`, and `get_vendor_details(vendor_id)` — all 3 were built later, in Problem 5, once the agent team actually needed them to fully work the 3 tickets (see below). `get_payment_history(kind, ref_id)` was considered again and deliberately **not** built — the `payments` table is still empty, and `accounting.md`/`facilities.md` already commit to flagging that gap honestly rather than guessing at payment history.

## MCP Tools, Round 2 (Problem 5)

Added once the agent team surfaced real gaps in resolving the 3 open tickets — each new tool closes one of those gaps:

| Tool | Table read | Ticket it unlocks | Why this tool is right for that ticket |
|------|-----------|--------------------|------------------------------------------|
| `get_pricing(sku)` | `pricing` | **103** — the bulk hoodie discount request | Nothing could evaluate whether a discount is financially sound without the real unit cost ($22) and list price ($58) — this tool gives Accounting the margin math instead of a guess. |
| `get_cash_balance(account_name)` | `cash_accounts` | **102** — the rent-due notice | `accounting.md` already commits to flagging a payment that would overdraw cash, but there was no way to check the balance at all — this tool gives Accounting the real $3,400 figure to check against the $2,400 rent. |
| `get_vendor_details(vendor_id)` | `vendors` | **101** — the out-of-stock tee order | Without this, nothing could tell the customer *when* to expect their tee — this tool follows the reprint invoice's `vendor_id` to Bulldog Print Co's real 5-day lead time instead of leaving the timeline unanswered. |

All 3 are owned by **Accounting** (not Inventory, even though "which vendor can restock" reads like an Inventory concern) — because the only way to discover a relevant `vendor_id` is through an invoice, which only Accounting can look up; Accounting is the agent that actually "deals directly with the vendors" in how the data flows, even if the underlying question originates from a stock shortfall.

### Agent ↔ MCP tool ↔ table

| Agent | MCP tools it can call | Table(s) |
|---|---|---|
| Boss | `get_inventory_level`, `get_lease_details`, `get_invoice_details`, `get_pricing`, `get_cash_balance`, `get_vendor_details` (all 6) | `inventory`, `leases`, `invoices`, `pricing`, `cash_accounts`, `vendors` |
| Inventory | `get_inventory_level` | `inventory` |
| Accounting | `get_invoice_details`, `get_inventory_level`, `get_pricing`, `get_cash_balance`, `get_vendor_details` | `invoices`, `inventory`, `pricing`, `cash_accounts`, `vendors` |
| Facilities | `get_lease_details` | `leases` |
| Customer Service | none (reaches data only via `ask_<agent>` delegation) | — |

## MCP Connection + Smoke Test (Problem 4)

The server is now connected to the vibe coder via `.mcp.json` at the project root (`Homework/5/.mcp.json`), registered as `campus-customs`, launched over stdio with an absolute path to both the Python interpreter and `mcp_server/server.py`. Getting this working required installing the `fastmcp-slim[server]` extra (the base install only has FastMCP's types, not the runtime needed to actually construct a server) and discovering that `.mcp.json` is only auto-detected at a session's own root — not a subfolder — which is why the file lives directly in `Homework/5/`, the session's working directory.

All 3 tools were tested live, one per ticket, by giving the vibe coder a natural-language prompt and letting it choose and call the right tool. Full evidence (prompt, tool name, tool input, and raw tool output) is in `output/mcp_smoke.json`. Every value returned matched `data/campus_customs_new.db` exactly:

- **Ticket 101**: "what white t-shirts are available in size S" → `get_inventory_level(CC-TEE-WHITE, S)` → `qty: 0` (confirmed out of stock, matching the ticket's premise).
- **Ticket 102**: "what's the rent situation, when's it due, how much is outstanding" → `get_lease_details(1)` → `$2,400/mo, due 2026-09-02`. The "how much is outstanding" part of the question went unanswered on purpose — `get_lease_details` only has rent terms, not payment status, and there's no payments/cash tool yet, so the smoke test records that gap rather than guessing a number.
- **Ticket 103**: "what other hoodies in size M are available" → `get_inventory_level(CC-HOOD-NAVY, M)` → `qty: 8`. "Other" hoodies don't exist — `CC-HOOD-NAVY` is the only hoodie SKU in the whole inventory table (confirmed in Problem 2), so reporting none is the correct, grounded answer rather than a limitation to apologize for.

## The Agent Team (Problem 5)

Five PydanticAI agents in `backend/`, one file each: `boss.py`, `inventory.py`, `accounting.py`, `facilities.py`, `customer_service.py`. Every agent:

- Uses the **same model** — `gpt-6-luna` routed through Portkey (`backend/runtime.py`, built once and shared, so every agent is guaranteed to use the same model rather than risking a typo/drift per file).
- Gets only the MCP tool(s) its own role needs — see "Per-agent tool scoping" under Security hardening below; this was originally one shared toolset for all 5 agents, then tightened to a structural per-agent restriction.
- Returns the **same structured output** — `AgentReply` (`backend/models.py`): a `message`, a `needs_human_approval` flag, and an optional `recommended_action`. One shared shape is what lets any agent parse any other agent's reply the same way.
- Loads its **system prompt** from its own file in `backend/prompts/` (`boss.md`, `inventory.md`, `accounting.md`, `facilities.md`, `customer_service.md`) — written by the student, not generated, per the assignment.

### Full connectivity (delegation)

`backend/team.py` is the only file that imports all 5 agents (each agent file only imports `runtime.py`, `models.py`, and `delegation.py` — never each other, which would be circular). It gives every agent an `ask_<other agent>` tool for each of the other 4, so any agent can delegate to any other agent (20 delegation tools total, 4 per agent). A delegation tool calls the target agent's `.run()` for real (not a stub) and returns its full `AgentReply`, sharing `usage` across the whole chain so token/cost tracking stays accurate across delegations.

Two structural guards (`backend/delegation.py`), not just prompt wording, stop the "agent loop" full connectivity could otherwise cause:

- **No repeat visits**: `DelegationDeps.chain` tracks every agent that's already touched the current ticket. If an agent tries to delegate to one already in the chain (e.g. Boss → Inventory → Boss), the tool raises `ModelRetry` instead of looping.
- **Hop cap**: `MAX_CHAIN_LENGTH = 4` — even a chain with no exact repeats (e.g. touching all 5 agents) is stopped past 4 hops.

### Ticket intake

`team.run_ticket(ticket_id)` reads one row straight from `tickets` in `data/campus_customs_new.db` (not through an MCP tool — ticket intake isn't one of the 3 tools built so far), formats it into a plain task description, and hands it to the Boss agent as the starting point of a chain (`chain=("boss",)`).

### Step-limit guard ("agent loops")

Every agent run (Boss's top-level run and every delegation call in `team.py`) is capped at `AGENT_STEP_LIMIT = 8` steps via PydanticAI's `UsageLimits(request_limit=...)` — a real "timeout" for an LLM agent means too many back-and-forth steps (repeating a lookup, looping between reasoning and tool calls), not wall-clock time. If an agent hits the cap, `UsageLimitExceeded` is caught and turned into a clear `AgentReply` instead of crashing:

- A **specialist or peer** hitting the cap returns a reply saying so, with `recommended_action` pointing at escalating to Boss to investigate — matching every prompt's existing Boss-only escalation path, just triggered by "my delegate got stuck" instead of "I'm blocked."
- **Boss itself** hitting the cap (in `run_ticket`) goes straight to `needs_human_approval: true`, since there's no agent above Boss to escalate to.

### The 5 prompts

All 5 are now written (by the student, in her own words — see each file's own "Source" section for the verbatim back-and-forth that shaped it):

- **`boss.md`** — always delegates real work to the right specialist(s) (can be more than one) and synthesizes their replies into one final decision; may use the MCP tools itself only to spot-check a surprising/high-stakes claim, run an independent audit when specialists disagree, or do a final grounding check before closing a high-stakes ticket — never to triage/route; propagates any delegate's `needs_human_approval` flag forward; flags a ticket to a human if it doesn't clearly fit Inventory/Accounting/Facilities/Customer Service's domains (e.g. HR, marketing, legal); explains plainly in its final reply if it had to stop delegating (already consulted an agent on this ticket, or hit the hop cap) instead of silently cutting off; escalates to a human directly if Boss itself can't resolve a ticket within its step limit.
- **`inventory.md`** — reports stock facts and shortfall analysis from `get_inventory_level` only, never commits to a sale or discount; says explicitly when restocking info (vendor/timeline) isn't available rather than guessing; all escalation goes through Boss only, never straight to a peer.
- **`accounting.md`** — validates transaction consistency (`get_invoice_details`, plus `get_inventory_level` only to cross-check, not to restock-check); traces every dollar figure to a real record instead of invoking full GAAP, which isn't checkable with 3 read-only tools; flags that customer payment history isn't trackable yet (no receivables table); Boss-only escalation, even for a lease question that's Facilities' domain; any real payment/purchase-order recommendation always needs human approval, pure info-sharing doesn't.
- **`facilities.md`** — resolves lease/rent tickets via `get_lease_details`; can state whether rent is due/overdue but not whether it was actually paid (no payments-table tool yet); utilities/equipment are explicitly out of scope until a tool exists for them, to be flagged to Boss as a future-tool suggestion rather than invented; Boss-only escalation.
- **`customer_service.md`** — the one agent allowed to ask peers (Inventory/Accounting/Facilities) directly for facts, to avoid bottlenecking live chat through Boss's ticket workflow; still escalates to Boss (not peers) for anything that's a decision rather than a fact; grounds every customer-facing claim in real tool data; offers a human handoff if a customer shows frustration after 1-2 unresolved exchanges.

### Grounding ("database only, never outside knowledge")

All 5 prompts now carry an explicit `## Grounding` section: an agent may only state what one of its own tool calls or a delegated agent's reply actually returned — never outside/general knowledge, even something that reads as harmless common sense (e.g., Customer Service answering general product-care advice unprompted). This is slightly stronger than the earlier "never make up data" wording in each prompt (which was about not inventing a value) — this rules out drawing on the model's own general/training knowledge at all when the database doesn't cover something, requiring an honest "I can't answer that from what's available" instead.

### Security hardening

Raised in conversation (not yet an assignment problem), implemented across the team:

**Per-agent tool scoping (structural, not just prompt wording).** Originally all 5 agents shared one `MCP_TOOLSETS` list — every agent was programmatically capable of calling all 3 tools, and "stay in your lane" was enforced only by what each prompt said. `runtime.py` now has `mcp_tools_for(*tool_names)`, which uses PydanticAI's `toolset.filtered(...)` to build an agent a toolset containing *only* the named tools — a tool outside an agent's domain isn't just discouraged, it's never visible to that agent's model at all:

| Agent | Tools it can actually call |
|---|---|
See "Agent ↔ MCP tool ↔ table" above for the current (Problem 5 Round 2) per-agent breakdown — Boss has all 6, Inventory only its own, Accounting its own plus `get_inventory_level` for consistency checks, Facilities only its own, Customer Service none directly.

**`needs_human_approval` as a hard checkpoint, not just a self-reported flag.** `backend/approvals.py` adds `record_pending_approval()`, called unconditionally by `run_ticket()` whenever a final reply sets `needs_human_approval: true` — this writes a durable, pending-by-default entry to `output/pending_approvals.json` that only a named human can move to `approved`/`rejected` via `approvals.decide()`; no code path marks one approved on its own. This is a different kind of gate from PydanticAI's native `toolset.approval_required(...)` + `DeferredToolResults` mechanism, which pauses an in-progress run until a human approves a specific *tool call* before it executes — that's the right mechanism for the moment a real action tool (a payment, a discount, a restock order) gets built, since right now all 3 MCP tools are read-only lookups with nothing to gate at the call level. Today's gate instead protects the ticket *decision* itself from being silently treated as resolved.

**Full audit trail.** `run_ticket()` now logs every run to `output/audit_trail.json` (append-only, never truncated, mirroring Homework 4's design choice): Boss's own top-level tool/delegation calls, plus every delegated specialist's own tool calls, in one trace per ticket (`boss_tool_calls` + `delegated_agent_calls`, tagged by agent), alongside the stop reason and duration. `DelegationDeps.audit` is the one field that's deliberately *shared* (not fresh per agent) across an entire ticket's call tree, specifically so every agent in a delegation chain logs into the same ordered record.

Verified: `mcp_tools_for()`'s generated allow-sets inspected directly and confirmed correct per agent; `approvals.py` unit-tested end-to-end (record → appears in `list_pending()` → `decide()` → no longer pending), test record then removed; whole team re-imported after all changes to confirm it still constructs with no errors. Still no live Portkey API calls.

## Safety

Guardrails a real business would want before letting this team touch real customers and real money:

- **No agent can act outside its own lane, structurally.** `runtime.py`'s `mcp_tools_for()` means Inventory literally cannot call `get_lease_details`, Facilities cannot call `get_invoice_details`, etc. — enforced by what's visible to each agent's model, not by hoping it follows its prompt.
- **Nothing executes money or commits the shop to anything.** All 6 MCP tools are read-only lookups. The one thing that looks like a "decision" (Boss's final reply) is gated, not autonomous: `needs_human_approval: true` unconditionally writes a durable `output/pending_approvals.json` entry (`backend/approvals.py`) that only a named human can approve or reject — nothing in the code path marks one approved on its own. The moment a real write/action tool is added (a payment, a discount, a restock order), PydanticAI's native `toolset.approval_required(...)` + `DeferredToolResults` is the mechanism to pause that specific tool call until a human signs off.
- **One decision-maker, always.** Every specialist escalates through Boss only — never agent-to-agent for a decision — so there's always a single point that synthesizes and is accountable for the final call (Customer Service's peer-to-peer exception is for facts only, never decisions).
- **Nothing is invented.** Every prompt has a `## Grounding` section: an agent can only state what a tool call or a delegated reply actually returned, never outside/general knowledge, even something that reads as harmless (e.g., generic product-care advice from Customer Service).
- **A capability gap becomes a human conversation, not a guess.** If any agent hits something no current tool covers, it flags Boss, and Boss is the one who surfaces "we may need a new tool for X" to the human — never silently invented, never silently dropped.
- **Full traceability.** `output/audit_trail.json` logs every tool call by every agent for every ticket run, append-only — so any of the above can be checked after the fact, not just trusted.

Limits that keep token use (and runaway cost) in check:

- **Per-agent step cap** — `AGENT_STEP_LIMIT = 8` (`backend/team.py`): any single agent's run is cut off after 8 steps (tool calls + reasoning turns) rather than being allowed to loop indefinitely, with a clear "this agent got stuck" signal instead of a silent hang.
- **Delegation hop cap** — `MAX_CHAIN_LENGTH = 4` (`backend/delegation.py`): a ticket can only pass through 4 agent-to-agent hops total, even if no single agent repeats, bounding the total cost of resolving any one ticket.
- **No repeat visits** — an agent already in a ticket's delegation chain can't be asked again, closing off the cheapest way to accidentally build an infinite (and infinitely expensive) loop.

### Status

Built and statically verified (`py_compile`, plus confirming the import graph constructs all 5 agents and all 20 delegation tools without errors) — **not run against the live Portkey API yet**, per the established pattern of building first and running only when asked.

## Planning the 3 Tickets (Problem 6)

Before wiring/running anything, wrote down expected agent behavior for each ticket in `output/desk_tickets.html` (double-click to open; one tab per ticket, plus empty Cash/Reflection tabs for later problems) — an Expected section (who Boss calls first and why, all delegations expected, which MCP tools expected) written by the student, and an Actual section left blank until the agents are actually run.

Surfaced one real gap while planning ticket 103: there's no way for this system to actually record a new sale/invoice to a customer. The `invoices` table only ever represents money the shop owes a **vendor** (every row requires a non-null `vendor_id`) — there's no sales ledger, no receivables table, and all 6 MCP tools are read-only, so even if there were a table, nothing could write to it. This is a real feature gap (a shop that can look at a sale but never record it happening), not a bug — but building it properly means a new table, a new **write** tool specifically gated with PydanticAI's `approval_required`/`DeferredToolResults` mechanism (set aside for exactly this moment back in the security-hardening round), and scope updates to at least Accounting's and Customer Service's prompts. Deliberately **not** built this problem — Boss's existing "flag a missing capability to the human" rule already covers this correctly: ticket 103's Expected section predicts the team surfaces this gap rather than inventing an invoice. Candidate for a future problem.

## Backend Routes (Problem 7)

`backend/main.py` — FastAPI app the React dashboard (Problem 8) will call. Built and statically verified (syntax checks, a full route-function integration test against scratch copies of the database — never the real working copy) but **never started as a live server and never actually called the live Portkey API** — that's for when the student starts it.

| Route | What it does |
|---|---|
| `GET /api/tickets` | All 3 tickets with their real current `status` (`open`/`resolved`) |
| `POST /api/tickets/{id}/run` | Hands the ticket to the real agent team (`team.run_ticket`) — the first route that actually calls the live model |
| `GET /api/events` | Flattens `output/audit_trail.json` into a list of events (agent, message, tool calls, timestamp) so the dashboard can refresh |
| `POST /api/approvals/{id}/approve` | The only route that moves real money — deducts cash and records the payment once a human approves |
| `GET /api/cash` | The real current `cash_accounts` balance |
| `POST /api/reset` | Archives the working DB + pending approvals, rebuilds a fresh working copy from the untouched seed |

### `AgentReply` grew a `category` (Problem 7)

Building the approve route surfaced a real gap: `needs_human_approval` alone doesn't say *why* — Boss getting stuck and Accounting recommending a $2,400 rent payment both set it, but only one involves money. `AgentReply` (`backend/models.py`) now has `category: "payment" | "review" | None`, plus `payment_amount`/`payment_account` (only set when `category == "payment"`). Accounting and Facilities — the only 2 agents whose approval-needing replies are ever about real money — now populate these when recommending a payment; Boss's prompt was updated to carry the exact values forward when synthesizing a specialist's flagged reply, rather than just passing along the bare boolean; Customer Service's frustrated-customer handoff is tagged `category: "review"` since it isn't about money.

### What "resolved" means (per the student's rule: real-$ tickets wait for a human)

`team.run_ticket()` marks a ticket `resolved` as soon as the team is done with it — **unless** the final reply is a `category: "payment"` approval request, in which case the ticket stays `open` until a human actually approves that specific payment. A `category: "review"` approval (Boss stuck, a frustrated customer) does **not** block resolution — the team's work is done either way; a human just also gets looped in separately via `pending_approvals.json`. `POST /api/approvals/{id}/approve` is what closes the loop: it applies the payment and marks the originating ticket `resolved`.

### The first real write (`backend/payments.py`)

Every MCP tool and every agent is still read-only. `payments.apply_payment()` is the one function in the whole system that writes — deducting `payment_amount` from `cash_accounts` and inserting a matching row into `payments` (`kind`/`ref_id` derived from the ticket's own `lease_id`/`invoice_id`, not asked of the model), both in one transaction so the two tables can't drift out of sync. It's never called by an agent — only by the approve route, after a human has already clicked approve.

### Reset without ever touching the audit trail (`backend/reset_db.py`)

Per the student's explicit call: `audit_trail.json` is never cleared, since it's meant to be the permanent record across every run including resets. Resetting instead **archives** (moves, doesn't delete) the current `campus_customs_new.db` and `pending_approvals.json` into `output/archive/reset_<ISO-timestamp-with-date>/`, rebuilds a fresh working copy from the untouched `campus_customs.db`, writes a fresh empty `pending_approvals.json`, and appends one marker entry to `audit_trail.json` noting the reset and where the old files went.

## Agent Dashboard (Problem 8)

React + Vite + TypeScript frontend in `frontend/`, built UI-first against realistic mock data (`src/mockData.ts`, drawn from the real seed tickets and the Problem 6 dialogue design) — not yet wired to the live `backend/main.py` routes, per plan (wiring is the next step).

**Creative direction** went through a real pivot: started with hand-authored pixel-art icons ("cozy Yale campus," Stardew-inspired), which had genuine readability problems (a bulldog that read as a horned animal, a hoodie that read as a house) even after several rounds of fixes — including adding an auto-outline feature to the sprite renderer and procedurally generating smooth circular/curved shapes via distance math instead of hand-guessing pixel grids. One sprite (a reference bulldog illustration) was dropped outright once the student confirmed it was Shutterstock stock art — not traced or closely replicated, since that would be a derivative of someone else's specific licensed work going into a submitted project. Ultimately the whole pixel-art direction was dropped as "odd looking," and the project pivoted twice more: first to a plain warm-parchment/serif-font direction (no custom art), then — mid-build — to a deliberately kitschy "MySpace 2002" retro theme in Yale colors (navy/gold diagonal-striped background, Comic Sans, an actual `<marquee>` banner, a glowing multi-shadow title, rainbow dividers, hard-shadow dashed-border panels, a fake LCD visitor counter, and a cursor sparkle trail), which is the current look.

**What it does** (all 7 behaviors from the assignment, verified live against mock data):

- Lists all 3 tickets with real status (`open`/`resolved`)
- Selecting a ticket and clicking "Run Agents" triggers a staged reveal of each agent's message (not all at once) — simulates what the real backend's `POST /api/tickets/{id}/run` + `GET /api/events` will eventually drive
- Each agent's message is shown with which MCP tool(s) it used, in a Boss → specialist order matching the real delegation design
- A ticket is marked resolved automatically once the run finishes — **unless** the final result is a real `category: "payment"` approval request, in which case it stays open until approved, exactly mirroring `run_ticket()`'s actual resolution rule from Problem 7
- A short per-agent summary appears once a run completes
- A pending payment shows an approval panel (amount + account); clicking approve marks it decided and is the only thing that moves the cash number
- The checking balance is shown in the header and visibly drops by the approved amount (tested live: $3,400.00 → $1,000.00 after approving ticket 102's $2,400 rent payment)

Verified end-to-end in the browser for both the plain and retro skins: ran ticket 101 (no money involved, auto-resolved), ran ticket 102 (stayed open, approval panel appeared), approved it (cash dropped, ticket resolved), reset the desk (state returned to the original 3 open tickets, $3,400). This was all against mock data at the time.

## Wiring to the Real Backend + First Live Runs

`src/api.ts` replaced every mock import with real `fetch` calls to `http://localhost:8000` — no mock data remains anywhere in the frontend. Added one backend route found missing while wiring: `GET /api/approvals` (optionally `?ticket_id=`), since the frontend has no other way to learn a pending approval's real `id` before calling the approve route.

### A real bug, found via the first live run: `reasoning_effort`

The very first real run (ticket 101) effectively hung, and an earlier run (ticket 103) had failed after 3 seconds with no reply. Root cause, found in the backend's own terminal output: `pydantic_ai.exceptions.ModelHTTPError: 400 ... "function tools with reasoning_effort are not supported for gpt-6-luna-global ... set reasoning_effort to 'none'."` — `pydantic_ai` auto-attaches a non-`"none"` reasoning effort for models it detects as reasoning-capable by name, which Azure's `gpt-6-luna` deployment rejects outright for any request using tools (i.e., every one of our agents, always). Fixed with one line in `runtime.py`: `OpenAIChatModel(..., settings=OpenAIChatModelSettings(openai_reasoning_effort="none"))` on the one shared `MODEL` object, so it applies to all 5 agents at once.

### Genuine live progress, not a fake spinner (`GET /api/tickets/{id}/live`)

Requested after the first slow run, to show what the agents are actually doing while a run is in flight (similar to how an LLM product might show its own reasoning trace). Rather than simulate this, `team.py` exposes the exact in-memory list each delegated agent is already appending to as it works (`DelegationDeps.audit`) via a small `_live_runs: dict[ticket_id -> list]`, readable from a separate concurrent request while the original run is still executing, and cleared the moment it ends. One real, documented limitation: Boss's own reasoning/tool calls only appear once the whole run finishes (it's a single blocking call) — but every delegated specialist's step is visible the moment it completes.

### A real behavioral bug, found from the first fully-working run

With the `reasoning_effort` bug fixed, ticket 101's run completed for real — and surfaced a genuine delegation problem: Boss delegated to Inventory with too little context (a specialist only ever sees what Boss writes in that one message, never the original ticket), so after Inventory found the one fact that mattered (0 in stock), it spent the rest of its steps trying to ask Boss and then Customer Service for "order context" nobody had given it, each attempt correctly blocked by the delegation-loop guard, until the whole run hit `AGENT_STEP_LIMIT` without Boss ever synthesizing a real answer. Notably, every safety mechanism from Problem 5 worked exactly as designed here — no infinite loop, no crash, no invented answer, correct fallback to `needs_human_approval`/`category: "review"` — this was a prompt quality problem, not a guardrail failure.

Fixed with 3 targeted prompt edits (each cited with the live-test evidence in that file's own `## Source` section): `boss.md` now tells Boss to include real ticket context in every delegation rather than a bare technical ask, and to only delegate to Customer Service for actual customer-facing chat, not an internal desk ticket just because a customer is named in it; `inventory.md` and `customer_service.md` both gained the same rule — a blocked escalation attempt means the target agent is already handling it, so answer with what's already known instead of trying someone else.

Also fixed a frontend bug the same live run exposed: `ApprovalPanel` was showing the full "Approve Payment" button for Boss's `category: "review"` flag (the step-limit timeout), even though there was no money to approve and clicking it would have hit the backend's real 400 rejection. The panel now branches on `category` — only a real `"payment"` entry gets the approve button; a `"review"` entry shows a plain, non-actionable "flagged for human review" notice instead.

The "show its thinking" request was finished end to end here too (only the backend half existed right after Problem 7): `api.ts` polls `GET /api/tickets/{id}/live` every second while a run is loading, rendering the genuine in-progress trace through the same `AgentFeed` component used for the final result, plus a live elapsed-seconds counter.

### A second real bug, found from the very next live run: shared usage pooled the step limit across agents

With the prompt fixes in place, the delegation confusion was gone — Inventory and Accounting both gave clean, correct, efficient answers (0 in stock; invoice 501 confirmed as a real $840 rush reprint). But Boss *still* hit the step limit and never produced a final answer. Root cause, found by reading PydanticAI's own `UsageLimits.check_before_request` source: `request_limit` checks the *cumulative* request count on whatever `RunUsage` object it's given — and `_make_delegate_tool`'s `delegate()` was passing the same shared `usage=ctx.usage` into every nested agent call (a deliberate Problem-5 choice, made so token/cost tracking would stay accurate across the whole delegation chain). The side effect: `AGENT_STEP_LIMIT = 8` was actually one pooled budget shared across Boss *and* every agent it delegates to combined, not 8 steps each as every prompt states — Inventory's and Accounting's own efficient steps were silently consuming the budget Boss needed for its own synthesis call.

Fixed by no longer sharing `usage` across the delegation boundary in `team.py` — each agent now gets its own fresh usage tracker, so its step cap is genuinely its own. Traded away cross-agent cumulative cost tracking to fix this, which nothing in the system currently reads or displays, so there was nothing real to lose.

The first fully successful real run (ticket 101, all 3 fixes together) validated the whole chain end to end — real `gpt-6-luna` calls, clean delegation, a genuine Boss-synthesized answer, correct non-payment review display, correct auto-resolve.

### A missing wall-clock backstop

Fixing the shared-usage bug (above) had a real side effect: removing the pooled budget also removed the only thing capping a ticket's *total* time, since each agent can now independently use up to `AGENT_STEP_LIMIT` (8) of its own real API round trips with nothing bounding the sum. A ticket 101 re-run took 100+ seconds with zero completed delegate steps yet (confirmed genuinely in-progress, not stuck, via `GET /api/tickets/101/live`). Added `TOTAL_RUN_TIMEOUT_SECONDS = 60` in `team.py` as the real backstop on the whole run (see below for how it's actually implemented — the first version of this fix introduced its own bug).

### A critical bug: `asyncio.run()` broke the MCP connection on the second-ever call

The first version of the wall-clock timeout above used `asyncio.run(asyncio.wait_for(boss_agent.run(...), timeout=60))` in place of `run_sync()`. It worked the first time, then broke every subsequent run in the same server process with `RuntimeError: Client failed to connect: Event loop is closed`. Root cause: `asyncio.run()` always creates a brand-new event loop and closes it at the end of every call, but the MCP server's client connection gets bound to whichever loop it first connects on — the second call's fresh loop couldn't reuse that connection. Confirmed by reading PydanticAI's own `run_sync()` source: it uses `loop.run_until_complete(...)` on one persistent loop that's *never* closed, specifically so this doesn't happen. Fixed by replicating that exact pattern — one module-level `_EVENT_LOOP = asyncio.new_event_loop()`, reused via `_EVENT_LOOP.run_until_complete(asyncio.wait_for(...))` for every call — rather than `asyncio.run()`. Verified properly: called `run_ticket()` for all 3 tickets back-to-back in one process (the exact failure condition), all 3 succeeded.

### "The answer" moved to the top, and a way to re-run a finished ticket

Two dashboard fixes from watching real runs: Boss's final message — already the real answer to the plain-English question — was buried as just another feed message, with a separate, less useful mechanical summary stuck at the bottom. Replaced that bottom block with a prominent "✅ the answer" panel directly under the question. Separately, the "Run Agents" button only ever appeared before a ticket's first run; added a "run again" button once a run completes, since testing (rightly) meant re-running the same ticket multiple times across fixes.

### Restoring history on load, and respecting a reset when doing it

A page reload (dev-server hot-reloads included) was silently discarding every ticket's results, since they only ever lived in the browser tab's memory. Fixed by having `loadAll()` also fetch recent history (`getEvents(300)`) and reconstruct each ticket's last real run on load — the backend is the actual source of truth, not whatever's left in memory. That fix then collided with reset: `audit_trail.json` is permanent and never cleared (even across a reset, by design — a reset just appends its own marker), so restoring "current" history was pulling in stale pre-reset runs right after a reset. Added `sinceLastReset()` (`api.ts`), which finds the most recent reset marker (`agent: "system"` in the events feed) and only restores history after it.

## Resolving the 3 Tickets for Real (Problem 9)

First official "resolve the tickets" run, executed directly against the live backend: reset (archived to `output/archive/reset_2026-10-13T04-27-22`), starting checking balance $3,400.00, all 3 tickets run to completion. Full results recorded in `output/desk_tickets.html`'s Actual sections, compared directly against the Problem 6 predictions.

- **101**: resolved cleanly (no human approval) — Boss → Inventory (0 on hand) + Accounting (invoice 501, plus an unprompted vendor lookup for the 5-day lead time). ~20s.
- **102**: a real gap — Boss → Facilities only; correctly caught that the recorded due date had already passed (genuinely overdue, not "due in 2 days"); flagged a `category: "payment"` approval for $2,400, but **never actually delegated to Accounting for a real cash account**, despite both Facilities' and its own reply saying to. Result: the pending approval's `payment_account` is `null` — clicking "Approve" on it right now would fail. Ticket correctly stayed `open`.
- **103**: the SKU+quantity fix from the previous follow-up held — Boss → Accounting (pricing) + Inventory (8 of 20 on hand, real shortfall), no Customer Service involvement, `category: "review"` (a discount decision, not a specific payment) — correctly didn't block auto-resolution.

The `payment_account: null` gap on ticket 102 is a known, recorded issue — not yet fixed, per instruction to do the run/record step first before the second part of Problem 9.

### Part 2 setup: fixing the payment-routing gap, and two more live findings

Before building the Part 2 artifacts (itemized cash, `resolved_tickets.json`, the finished harness), revisited ticket 102's `payment_account: null` gap directly. `facilities.md` and `accounting.md` already said the right things (Facilities: flag the missing account to Boss; Accounting: never set `category: "payment"` without a real account) — the actual gap was `boss.md`, which received that exact instruction back from both and never acted on it. Added a rule to `boss.md`'s Output section: delegate to Accounting yourself for the real account before finalizing a payment flag, never pass one along with a missing or guessed account (wording proposed, student signed off directly).

**Reset + full re-run, attempt 1** (after the `boss.md` fix alone): Boss correctly delegated to Accounting this time — a real behavior change from before — but Accounting then refused to recommend the payment at all. It read `cash_accounts.date` (2026-08-31) as a staleness signal relative to `desk.date_today` (2026-10-13) and flagged `category: "review"` instead, with no payment fields at all. Ticket 102 still resolved (a review flag doesn't block resolution) but with zero cash movement and nothing left to approve — not a loop or invented data, just an overly literal reading of a last-updated timestamp that nothing in the system ever treats as an expiry signal. Clarified in `accounting.md`'s Tool use section: that `date` field is a last-updated stamp, not a staleness warning — treat the balance as current unless an actual payment has been recorded against it since.

**Re-run, attempt 2** (after the `accounting.md` clarification): Accounting correctly recommended the $2,400 rent payment from `checking`; Boss's final reply carried forward a real, actionable `category: "payment"`, `payment_amount: 2400`, `payment_account: "checking"` for the first time this problem. This is the run the Part 2 cash ledger is built from.

Two more real findings surfaced in that same run — documented here (same "known, recorded" treatment as the original gap above) rather than chased with a third prompt edit, since the core payment fields are now correct and the student explicitly chose to record rather than keep fixing:

- **Facilities bypassed its own Boss-only escalation rule.** Its reply shows it calling `ask_accounting` directly — a tool it structurally has access to under the full-connectivity delegation design even though `facilities.md` explicitly forbids using it ("you never delegate directly to Inventory, Accounting, or Customer Service"). Likely triggered by Boss's own task wording to Facilities that run ("confirm the cash account needed with Accounting"), which reads ambiguously as permission to ask directly rather than flag it back to Boss. The end result was still correct (same account/amount Boss would have obtained anyway), but it's a real gap between what the prompt forbids and what the tool wiring still permits.
- **Inconsistent date reasoning in Boss's own synthesis.** That run's final reply states rent is "due on 2026-09-02, consistent with the email stating it is due in two days" — which is wrong; relative to the shop's actual current date, that due date is well over a month past. An earlier run (documented above) correctly caught this same ticket as overdue. Non-deterministic across runs, and untouched by either of this round's prompt edits.

### Problem 9, Part 2 — Itemized cash, resolved records

With the payment-routing gap verified fixed, ran all 3 tickets to completion against the same clean reset and built the Part 2 deliverables directly from the real resulting state (`audit_trail.json`, `pending_approvals.json`, `cash_accounts`, `payments`) — nothing here is predicted or invented.

**Final run results:**
- **101**: resolved, no cash impact. Boss delegated to Inventory (0 on hand), Accounting (invoice 501 confirmed open/unpaid), and Customer Service (couldn't confirm fulfillment, flagged a non-blocking `category: "review"`).
- **102**: resolved, **$2,400.00 paid**. Boss delegated to Facilities, which got the real `checking` account from Accounting; Boss itself also grounded the final number with its own `get_cash_balance` call. Flagged a real `category: "payment"` approval; the student approved it live in the dashboard (`decided_by: rachel.sin@yale.edu`), and `payments.apply_payment()` recorded payment id 1 and deducted the cash in one transaction.
- **103**: resolved, no cash impact. Boss delegated to Inventory (8 of 20 on hand, shortfall 12) and Accounting (10% illustrative bulk discount, $52.20/unit); no human approval needed this run — a cleaner, more confident synthesis than an earlier same-day run on the identical facts, which had flagged a non-blocking review item instead. Documented both outcomes in `desk_tickets.html` rather than picking one.

**`output/desk_tickets.html`** — all 3 Actual sections rewritten against this final official run (the earlier Problem 9 Actual text, written before the payment-routing bug was found, is preserved inline as "an earlier same-day run" where the two runs genuinely differed, rather than erased). Expected sections untouched throughout.

**Cash tab**, built and reconciled directly against the real database rather than computed by hand:

| | Amount | Why |
|---|---|---|
| Starting balance (post reset, 2026-10-13T20:23:27) | $3,400.00 | — |
| #101 | $0.00 | No payment recommended or executed — a customer-order/fulfillment question, not a shop payment. |
| #102 | &minus;$2,400.00 | Lease 1 rent to Elm City Properties, approved by the student, applied via `payments.apply_payment()`. |
| #103 | $0.00 | Discount is an unapproved pricing recommendation only — no sales/receivables tool exists to actually charge the customer (known gap since Problem 6). |
| **Ending balance** | **$1,000.00** | Verified to match `cash_accounts.balance` in `data/campus_customs_new.db` exactly. |

**`output/resolved_tickets.json`** — one entry per ticket: `id`, `final_status`, `short_outcome`, `agent_contributions` (one sentence per agent that actually touched the ticket, not a generic list of all 5), and `human_approvals` (the real approval record(s) from `pending_approvals.json`, including the approved one's `decided_by`/`decided_at` for 102, and an empty list for 103 since none was ever created).

**`output/audit_trail.json`** — append-only by design (see Problem 7); this round's real runs (the reset, both 102 re-runs, and the final 101/102/103 runs) are already in it as a natural side effect of running tickets against the live backend, bringing the file to 96 entries total across every problem's testing. No separate "append" step was needed or taken — recording every real run was already the system's job from Problem 5 onward.

**`output/resolved_board.html`** (dashboard screenshots per resolved ticket) — deliberately **not built this pass**, per the student's own call ("yeah we'll make that later on i think?").

### A new feature: payment-status confirmation

Raised by the student after seeing Accounting dead-end on a ticket instead of asking her anything ("shouldnt it ask me to approve?"): when Accounting has a real amount and account ready but genuinely can't confirm whether it's already been paid (no payment-history tool exists), the old behavior was to withhold the recommendation entirely, leaving nothing for a human to act on. Designed and built a real fix rather than just documenting the gap:

- **New `AgentReply.category` value**: `"payment_pending_confirmation"` (`backend/models.py`) — carries the same `payment_amount`/`payment_account` as a normal `"payment"` flag, but signals that a human needs to confirm payment status first rather than just approve.
- **`accounting.md`** now tells Accounting to use this category instead of withholding the recommendation when it can't confirm payment status (first wording draft didn't actually name the new category — caught and refined after the student flagged it).
- **`boss.md`** got a matching carry-forward rule, since without it Boss's existing category-propagation logic (which only knew `"payment"`/`"review"`) had no instruction for a category it didn't recognize.
- **`POST /api/approvals/{id}/confirm-payment-status`** (`backend/main.py`) — the human answers one yes/no question. Not yet paid: behaves exactly like a normal approval (moves the cash). Already paid: nothing is paid (no duplicate), but the ticket still resolves, since the open question is answered either way. Refactored the payment `kind`/`ref_id` derivation into one shared helper used by both approve routes.
- **Frontend**: `ApprovalPanel.tsx` got a new branch — a "has this already been paid?" panel with two buttons instead of a blind "Approve," plus a corrected settled-state label so "already paid, no duplicate sent" doesn't read as a rejection.

Deliberately kept the yes/no mechanic itself out of the prompt (the student asked directly whether to spell it out there) — consistent with every other prompt in this project, which specifies structured output only, never UI mechanics; the category name alone carries what the implementation needs.

Verified live, end to end, by the student herself: reset → ran ticket 102 once → Accounting correctly flagged `category: "payment_pending_confirmation"` with a real $2,400/`checking` → she clicked "No, pay it" → cash deducted, ticket resolved, approval recorded as `approved` under her name. Screenshots saved to `output/screenshots/` for the eventual `resolved_board.html`.

Two real bugs surfaced and fixed along the way, both in `backend/approvals.py`'s `list_pending()`:
- **First bug**: re-running a ticket can leave an older, never-decided approval behind; the dashboard was showing whichever pending entry it found for a ticket, which was sometimes a stale one from an earlier, since-superseded run (visible in a student-provided screenshot: a "flagged for review" box quoting a different, outdated run). Fixed by deduping to each ticket's most recent *pending* entry.
- **Second bug**, found while testing the fix above: that dedup only compared among pending entries, so once the real/current approval got decided, an older never-decided entry could resurface as if it were still live. Fixed by comparing each ticket's single most recent entry overall (any status) and only surfacing it if that one is still pending.

### Status

Tables, MCP tools (both rounds), the 5-agent team and its delegation/security design, the backend's 8 routes (7 from Problem 7 plus this problem's `confirm-payment-status`), the React dashboard, and the safety-rules recap are all documented above across the Problem 2/3/5/7/8/9 sections; this section closes out Problem 9 end to end except for `resolved_board.html`, held for a later pass.
