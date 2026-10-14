# Dashboard Design (Problem 8)

What was chosen for the Campus Customs agent desk, and why.

## Creative direction

Went through 3 real iterations, not one:

1. **Hand-pixeled "cozy Yale campus" art** (a bulldog, a hoodie, a coin, a tower, a ledger, a varsity-style "Y") — dropped after multiple rounds of fixes still didn't read right at a glance (a bulldog that looked like a horned animal, a hoodie that looked like a house). One reference image turned out to be licensed Shutterstock stock art, so it was dropped outright rather than traced/closely replicated — a recolored copy is still a derivative of someone else's specific artwork, and this project gets submitted.
2. **A plain "warm parchment, Yale Blue, serif headings" direction** — clean, safe, and genuinely boring. Correctly called out as "not creative."
3. **The final direction: a deliberately kitschy "MySpace, 2002" theme in Yale colors.** Solid Yale-blue background, Comic Sans everywhere, an actual `<marquee>` banner, a glowing drop-shadowed "~*✧･ﾟ YALE ･ﾟ✧*~" title, rainbow-animated dividers and text, chunky dashed borders with hard offset drop-shadows instead of soft card shadows, a fake black-and-green LCD "visitor counter," blinking "OPEN!!" badges, and a cursor sparkle trail. This is "a real desk people would want to sit at" via personality and nostalgia rather than polish — genuinely distinct from a generic admin-panel template, and more fun to actually use.

## Layout

Two-column desk: a **ticket board** on the left (all 3 tickets, always visible, click to switch), and a **detail panel** on the right for whichever ticket is selected. A header pins the shop identity, the live checking balance, and a reset control above both columns; a footer carries the era-appropriate kitsch (visitor counter, "best viewed in Netscape Navigator," last-updated line) so it doesn't compete with the working area.

Chosen over a single long scrolling page specifically because the task is fundamentally "pick one of a few things, then focus on it" — a persistent board plus a focused detail view matches that better than a ticket you'd have to scroll back up to leave.

## How agents read differently

Every agent gets its own fixed color (Boss = Yale blue, Inventory = sage green, Accounting = gold, Facilities = brown, Customer Service = dusty red), used consistently for its name, its message card's border, and its drop-shadow — so scanning down the feed, *who said what* is readable from color alone before even reading the name. Each message also shows which MCP tool(s) that agent called (e.g. `get_inventory_level`) in a small tag, so a tool call is visually distinguished from the agent's own reasoning/wording.

**Which model is running** was a gap flagged after the fact (Problem 8, follow-up): nothing in the UI said what AI was actually behind "Boss" or "Inventory." Since every agent in this system is required to run on the same model (course constraint: `gpt-6-luna` via Portkey, enforced in `backend/runtime.py`), this isn't a per-event fact that needs fetching — it's a fixed, system-wide one. Added a header-level badge ("🧠 every agent runs on gpt-6-luna via Portkey") for overall transparency, plus a small model tag next to each agent's name in the feed itself, so the answer is visible right where the confusion was (reading an agent's message and not knowing what's actually generating it).

## Resolved tickets and cash

A ticket's status badge is a blinking amber "OPEN!!" or a static sage-green "✓ done!!" — blinking specifically for *open*, since that's the state that still needs attention; a resolved ticket shouldn't visually compete for attention anymore. This isn't decided client-side: the dashboard reflects whatever `tickets.status` the backend actually returns, and the backend's own rule (`team.run_ticket()`, Problem 7) is that a ticket resolves the moment the team is done with it **unless** the result is a real `category: "payment"` approval request — in which case it stays open until a human approves it. The UI surfaces that exact distinction: a run that needs money shows a dedicated approval panel (the exact amount and account) instead of silently finishing, and the ticket visibly stays "OPEN!!" until that panel is acted on.

Cash is pinned in the header, not buried in the ticket detail, since it's shop-wide state that matters regardless of which ticket is selected — and it's the one number in the whole dashboard that a human approving a payment needs to trust is real and current, so it always reflects a fresh `GET /api/cash` call rather than being computed client-side from guesses.

## Status

Fully wired to the real backend (`http://localhost:8000`) — no mock data remains in the frontend. `GET /api/tickets`, `/api/cash`, and `/api/approvals` load on startup; clicking "Run Agents" calls the real `POST /api/tickets/{id}/run` (a genuine Portkey/`gpt-6-luna` call), then re-fetches events/tickets/approvals/cash to reflect what actually happened, with a staged reveal of the agent feed for readability. Approving a payment calls the real `POST /api/approvals/{id}/approve`.
