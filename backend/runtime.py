"""Shared runtime pieces every agent in the team is built from: the one
Portkey-routed model (so every agent uses gpt-6-luna consistently, never a
different model by accident) and the one MCP toolset (so every agent reads
the shop's real data through the same 3 tools, per Problem 3/4).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.mcp import load_mcp_toolsets
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

# backend/runtime.py -> backend -> Homework 5 root (.env and .mcp.json live here).
REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
MCP_CONFIG_PATH = REPO_ROOT / ".mcp.json"

load_dotenv(ENV_PATH)

PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
if not PORTKEY_API_KEY:
    raise RuntimeError(f"PORTKEY_API_KEY not found — expected it in {ENV_PATH}")

# Built as an explicit client (not os.environ) so the key only ever flows
# into this one client, never printed or persisted anywhere.
_openai_client = AsyncOpenAI(
    api_key=PORTKEY_API_KEY,
    base_url="https://api.portkey.ai/v1",
    timeout=20.0,
    max_retries=1,
)

# Azure's gpt-6-luna deployment rejects function/tool calls made with a
# reasoning_effort set (pydantic_ai defaults non-"none" reasoning effort for
# models it detects as reasoning-capable by name) -- every one of our agents
# relies on tool calls, so this has to be forced off here, once, for the
# whole shared model, not per agent.
MODEL = OpenAIChatModel(
    "gpt-6-luna",
    provider=OpenAIProvider(openai_client=_openai_client),
    settings=OpenAIChatModelSettings(openai_reasoning_effort="none"),
)

# One toolset per server in .mcp.json (just "campus-customs" for now), shared
# across every agent so they all see the same 3 tools built in Problem 3.
MCP_TOOLSETS = load_mcp_toolsets(MCP_CONFIG_PATH)

# The server name in .mcp.json -- load_mcp_toolsets() prefixes every tool
# name with this (e.g. "get_inventory_level" -> "campus-customs_get_inventory_level").
_MCP_SERVER_NAME = "campus-customs"


def mcp_tools_for(*tool_names: str):
    """Restrict the shared MCP toolset down to just the given tool names,
    e.g. mcp_tools_for("get_lease_details") for Facilities. A STRUCTURAL
    boundary, not just a prompt instruction -- an agent built this way
    cannot call a tool outside its own domain even if its prompt were
    ignored, because the tool is never visible to it in the first place.
    Call with no arguments for an agent that shouldn't have any direct MCP
    tool at all (e.g. Customer Service, which only delegates to peers)."""
    allowed = {f"{_MCP_SERVER_NAME}_{name}" for name in tool_names}
    return [toolset.filtered(lambda ctx, tool_def: tool_def.name in allowed) for toolset in MCP_TOOLSETS]
