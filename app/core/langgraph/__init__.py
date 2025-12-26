"""LangGraph integration for AI agent workflows.

This package provides a modular LangGraph implementation with:
- State management (AgentState)
- Graph building (GraphBuilder)
- Node definitions (AgentNodes)
- Tool integration including MCP support
- Main agent interface (LangGraphAgent)

MCP Search Setup (set environment variables):
- BRAVE_API_KEY for Brave Search
- TAVILY_API_KEY for Tavily Search
- EXA_API_KEY for Exa Search

Example usage:
    from app.core.langgraph import LangGraphAgent

    agent = LangGraphAgent()
    await agent.initialize()  # Auto-configures MCP search tools

    response = await agent.get_response(
        messages=[Message(role="user", content="Search for AI news")],
        session_id="123",
    )
"""

from app.core.langgraph.agent import LangGraphAgent
from app.core.langgraph.builder import GraphBuilder, create_default_graph
from app.core.langgraph.nodes import AgentNodes
from app.core.langgraph.state import AgentState, MCPServerConfig, ToolCallResult
from app.core.langgraph.tools import (
    # Tool collections
    builtin_tools,
    get_all_tools,
    tools,
    # Fallback web search tools
    web_search,
    news_search,
    search,
    web_search_tools,
    # MCP manager
    mcp_manager,
    setup_default_mcp_servers,
    # MCP server configs - general
    create_filesystem_mcp_config,
    create_fetch_mcp_config,
    create_memory_mcp_config,
    create_puppeteer_mcp_config,
    # MCP server configs - search
    create_brave_search_mcp_config,
    create_tavily_search_mcp_config,
    create_exa_search_mcp_config,
    get_default_search_mcp_configs,
)

# Backward compatibility: keep graph.py working
# The old LangGraphAgent class is now in agent.py
from app.core.langgraph.agent import LangGraphAgent as Agent

__all__ = [
    # Main interface
    "LangGraphAgent",
    "Agent",
    # Building blocks
    "GraphBuilder",
    "AgentNodes",
    "AgentState",
    "create_default_graph",
    # State types
    "ToolCallResult",
    "MCPServerConfig",
    # Tools
    "tools",
    "builtin_tools",
    "get_all_tools",
    # Fallback web search tools
    "web_search",
    "news_search",
    "search",
    "web_search_tools",
    # MCP
    "mcp_manager",
    "setup_default_mcp_servers",
    # MCP general configs
    "create_filesystem_mcp_config",
    "create_fetch_mcp_config",
    "create_memory_mcp_config",
    "create_puppeteer_mcp_config",
    # MCP search configs
    "create_brave_search_mcp_config",
    "create_tavily_search_mcp_config",
    "create_exa_search_mcp_config",
    "get_default_search_mcp_configs",
]
