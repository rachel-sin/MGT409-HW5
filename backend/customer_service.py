"""Customer Service agent -- drafts messages for customers. Shop-rules
system prompt is written by the student in prompts/customer_service.md, not
generated here.
"""

from pathlib import Path

from pydantic_ai import Agent

from delegation import DelegationDeps
from models import AgentReply
from runtime import MODEL, mcp_tools_for

SYSTEM_PROMPT = (Path(__file__).resolve().parent / "prompts" / "customer_service.md").read_text()

# No direct MCP tool at all -- a structural match for customer_service.md's
# "you have no dedicated database tool of your own" rule. It only reaches
# real data through its ask_<agent> delegation tools (added in team.py).
customer_service_agent = Agent(
    MODEL,
    output_type=AgentReply,
    system_prompt=SYSTEM_PROMPT,
    deps_type=DelegationDeps,
    toolsets=mcp_tools_for(),
)
