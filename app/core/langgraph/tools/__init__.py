"""LangGraph tools for enhanced language model capabilities.

This package contains custom tools that can be used with LangGraph to extend
the capabilities of language models. 

Tool Priority:
1. MCP tools (if configured) - Brave Search, Tavily, Exa, Fetch
2. Built-in tools (fallback) - DuckDuckGo search

MCP Search Setup:
- Set BRAVE_API_KEY for Brave Search
- Set TAVILY_API_KEY for Tavily Search  
- Set EXA_API_KEY for Exa Search
- Fetch MCP is always available (no API key needed)
"""

from langchain_core.tools import BaseTool

from .mcp_tools import (
    MCPToolManager,
    mcp_manager,
    # MCP server configs
    create_filesystem_mcp_config,
    create_fetch_mcp_config,
    create_memory_mcp_config,
    create_puppeteer_mcp_config,
    # Search MCP configs
    create_brave_search_mcp_config,
    create_tavily_search_mcp_config,
    create_exa_search_mcp_config,
    get_default_search_mcp_configs,
    setup_default_mcp_servers,
    MCPServerConfig,
)
from .web_search import (
    duckduckgo_search_tool,
    web_search,
    news_search,
    search,
    web_search_tools,
    get_web_search_tools,
)
from .teams_tools import (
    teams_tools,
    # Calendar & Tasks
    create_reminder,
    create_meeting,
    get_my_calendar,
    # Messaging
    send_teams_message,
    # Users & Teams
    get_team_members,
    get_user_info,
    search_users,
    get_my_profile,
    get_user_presence,
)

# Fallback built-in tools (used when no MCP search is configured)
_fallback_tools: list[BaseTool] = list(web_search_tools) + teams_tools


async def get_all_tools(use_mcp_search: bool = True) -> list[BaseTool]:
    """Get all available tools, prioritizing MCP tools.

    Args:
        use_mcp_search: If True, set up MCP search servers automatically

    Returns:
        list[BaseTool]: All available tools
    """
    tools_list = []

    # Set up default MCP search servers if requested
    if use_mcp_search:
        setup_default_mcp_servers()

    # Initialize MCP tools
    mcp_tools = await mcp_manager.initialize()

    if mcp_tools:
        # Use MCP tools (includes search if configured)
        tools_list.extend(mcp_tools)

        # Check if we have any search capability from MCP
        mcp_tool_names = [t.name for t in mcp_tools]
        has_mcp_search = any(
            "search" in name.lower() or "fetch" in name.lower()
            for name in mcp_tool_names
        )

        # Only add fallback search if no MCP search available
        if not has_mcp_search:
            tools_list.extend(_fallback_tools)
    else:
        # No MCP tools, use fallback
        tools_list.extend(_fallback_tools)

    return tools_list


# For backward compatibility - synchronous access to fallback tools only
builtin_tools: list[BaseTool] = _fallback_tools
tools: list[BaseTool] = _fallback_tools

__all__ = [
    # Legacy/backward compatibility
    "tools",
    "builtin_tools",
    "duckduckgo_search_tool",
    # Built-in web search (fallback)
    "web_search",
    "news_search",
    "search",
    "web_search_tools",
    "get_web_search_tools",
    # Teams tools
    "teams_tools",
    "create_reminder",
    "create_meeting",
    "get_my_calendar",
    "send_teams_message",
    "get_team_members",
    "get_user_info",
    "search_users",
    "get_my_profile",
    "get_user_presence",
    # Main tool getter
    "get_all_tools",
    # MCP manager
    "MCPToolManager",
    "mcp_manager",
    "MCPServerConfig",
    "setup_default_mcp_servers",
    # MCP server configs - general
    "create_filesystem_mcp_config",
    "create_fetch_mcp_config",
    "create_memory_mcp_config",
    "create_puppeteer_mcp_config",
    # MCP server configs - search
    "create_brave_search_mcp_config",
    "create_tavily_search_mcp_config",
    "create_exa_search_mcp_config",
    "get_default_search_mcp_configs",
]
