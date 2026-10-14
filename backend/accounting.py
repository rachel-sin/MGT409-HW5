"""Accounting agent -- watches cash and invoices, checks margins, and
prepares payments or purchase orders for human approval. Shop-rules system
prompt is written by the student in prompts/accounting.md, not generated
here.
"""

from pathlib import Path

from pydantic_ai import Agent

from delegation import DelegationDeps
from models import AgentReply
from runtime import MODEL, mcp_tools_for

SYSTEM_PROMPT = (Path(__file__).resolve().parent / "prompts" / "accounting.md").read_text()

# Its own tools (invoices, pricing, cash, vendors -- the money-and-vendor
# side of the shop) plus inventory for transaction-consistency checks only
# -- never get_lease_details, which belongs to Facilities.
accounting_agent = Agent(
    MODEL,
    output_type=AgentReply,
    system_prompt=SYSTEM_PROMPT,
    deps_type=DelegationDeps,
    toolsets=mcp_tools_for(
        "get_invoice_details", "get_inventory_level", "get_pricing", "get_cash_balance", "get_vendor_details"
    ),
)
