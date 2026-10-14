"""Facilities agent -- handles the shop space side (leases, rent, etc.).
Shop-rules system prompt is written by the student in prompts/facilities.md,
not generated here.
"""

from pathlib import Path

from pydantic_ai import Agent

from delegation import DelegationDeps
from models import AgentReply
from runtime import MODEL, mcp_tools_for

SYSTEM_PROMPT = (Path(__file__).resolve().parent / "prompts" / "facilities.md").read_text()

# Only its own tool -- a structural match for facilities.md's "don't branch
# into get_invoice_details or get_inventory_level" rule.
facilities_agent = Agent(
    MODEL,
    output_type=AgentReply,
    system_prompt=SYSTEM_PROMPT,
    deps_type=DelegationDeps,
    toolsets=mcp_tools_for("get_lease_details"),
)
