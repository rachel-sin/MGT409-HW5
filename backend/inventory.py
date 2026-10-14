"""Inventory agent -- checks stock by SKU and size, spots shortfalls, and
figures out which vendor can restock. Shop-rules system prompt is written
by the student in prompts/inventory.md, not generated here.
"""

from pathlib import Path

from pydantic_ai import Agent

from delegation import DelegationDeps
from models import AgentReply
from runtime import MODEL, mcp_tools_for

SYSTEM_PROMPT = (Path(__file__).resolve().parent / "prompts" / "inventory.md").read_text()

# Only its own tool -- a structural match for inventory.md's "stick to your
# own tool" rule, not just a prompt instruction.
inventory_agent = Agent(
    MODEL,
    output_type=AgentReply,
    system_prompt=SYSTEM_PROMPT,
    deps_type=DelegationDeps,
    toolsets=mcp_tools_for("get_inventory_level"),
)
