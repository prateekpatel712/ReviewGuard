"""
ReviewGuard — MCP Client.
Loads and exposes Model Context Protocol (MCP) tools from the local JSON config.
"""

import json
from pathlib import Path
from typing import List

from langchain_core.tools import BaseTool

from config import settings

# In a real environment, you might need an active async session context for MCP
# to keep the stdio pipes alive. This module provides a skeletal synch interface 
# expecting langchain_mcp_adapters's load_mcp_tools to handle connection orchestration.

try:
    from langchain_mcp_adapters.tools import load_mcp_tools
except ImportError:
    # Fallback to prevent immediate crash if not installed
    def load_mcp_tools(*args, **kwargs):
        print("[mcp_client] langchain-mcp-adapters is not installed.")
        return []

CONFIG_PATH = Path(__file__).resolve().parent.parent / "mcp_config.json"


def get_mcp_tools() -> List[BaseTool]:
    """
    Reads the mcp_config.json file and loads all configured MCP tools.
    """
    if not CONFIG_PATH.exists():
        print(f"[mcp_client] Config file not found: {CONFIG_PATH}")
        return []

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    # Substitute env vars in config blocks
    mcp_servers = config_data.get("mcpServers", {})
    for server_name, server_cfg in mcp_servers.items():
        env_dict = server_cfg.get("env", {})
        if "GMAIL_CREDENTIALS" in env_dict and "${GMAIL_CREDENTIALS_PATH}" in env_dict["GMAIL_CREDENTIALS"]:
            env_dict["GMAIL_CREDENTIALS"] = settings.gmail_credentials_path
        if "GOOGLE_CREDENTIALS" in env_dict and "${GOOGLE_CREDENTIALS_PATH}" in env_dict["GOOGLE_CREDENTIALS"]:
            env_dict["GOOGLE_CREDENTIALS"] = settings.google_credentials_path

    # Load all configured tools
    # NOTE: Actual adapter APIs may require async session management.
    # We pass the replaced config to load_mcp_tools as a stub.
    try:
        tools = load_mcp_tools(config_data)
        return tools
    except Exception as exc:
        print(f"[mcp_client] Error loading MCP tools: {exc}")
        return []


def get_gmail_tools() -> List[BaseTool]:
    """
    Returns the loaded MCP tools filtered for Gmail operations.
    """
    tools = get_mcp_tools()
    # Assuming tool names contain 'gmail'
    return [t for t in tools if "gmail" in t.name.lower()]


def get_sheets_tools() -> List[BaseTool]:
    """
    Returns the loaded MCP tools filtered for Google Sheets operations.
    """
    tools = get_mcp_tools()
    # Assuming tool names contain 'sheet'
    return [t for t in tools if "sheet" in t.name.lower()]
