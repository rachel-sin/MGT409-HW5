# Campus Customs MCP Server

A FastMCP server that gives every agent in the Campus Customs Multi-Agent Operations system a shared, read-only "tool belt" into the shop's real data. Agents call these tools instead of guessing at stock, rent, or invoice facts — nothing here is invented.

## Database

Reads `data/campus_customs_new.db` — the working copy made in Problem 2 (`data/campus_customs.db` is the original seed and is never touched by this server or any agent).

## Tools

Built in Problem 3 (first 3) and Problem 5 (last 3, added once the agent team needed them to fully work the open tickets):

- **`get_inventory_level(sku, size)`** — reads the `inventory` table. Returns the real on-hand quantity for one SKU/size, or says plainly that no record exists.
- **`get_lease_details(lease_id)`** — reads the `leases` table. Returns the real monthly rent, next due date, and landlord for one lease.
- **`get_invoice_details(invoice_id)`** — reads the `invoices` table. Returns the real amount, due date, status, and description for one invoice.
- **`get_pricing(sku)`** — reads the `pricing` table. Returns the real unit cost and list price for one SKU.
- **`get_cash_balance(account_name)`** — reads the `cash_accounts` table. Returns the real balance and as-of date for one cash account.
- **`get_vendor_details(vendor_id)`** — reads the `vendors` table. Returns a vendor's real name, specialty, and lead time.

See `output/harness.md` for how each tool ties to a specific open ticket, and which agent is allowed to call it (each agent's toolset is now structurally restricted to its own domain, not just a prompt rule).

## Running it

Connected to the vibe coder as of Problem 4 via `.mcp.json` at the project root (`Homework/5/.mcp.json`), registered as `campus-customs`, launched over stdio with absolute paths to the Python interpreter and `server.py`. The first 3 tools were smoke-tested against real natural-language prompts — see `output/mcp_smoke.json` for the prompts, tool calls, and outputs, and `output/harness.md` for the write-up. (The 3 tools added in Problem 5 were verified by calling them directly in Python against the database, not yet re-smoke-tested through the vibe coder connection, which would need a session restart to pick up the new tools.)
