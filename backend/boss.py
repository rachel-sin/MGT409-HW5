"""Boss agent -- reads each ticket, decides who should work on it, and makes
final calls. Shop-rules system prompt is written by the student in
prompts/boss.md, not generated here.
"""

from pathlib import Path

from pydantic_ai import Agent

from delegation import DelegationDeps
from models import AgentReply
from runtime import MODEL, mcp_tools_for

SYSTEM_PROMPT = (Path(__file__).resolve().parent / "prompts" / "boss.md").read_text()

# All 6 tools, matching boss.md's 3 carve-out cases for when Boss may use a
# tool itself (spot-checking a claim, resolving a disagreement, a final
# grounding check) -- it doesn't know in advance which one a ticket needs.
boss_agent = Agent(
    MODEL,
    output_type=AgentReply,
    system_prompt=SYSTEM_PROMPT,
    deps_type=DelegationDeps,
    toolsets=mcp_tools_for(
        "get_inventory_level",
        "get_lease_details",
        "get_invoice_details",
        "get_pricing",
        "get_cash_balance",
        "get_vendor_details",
    ),
)
