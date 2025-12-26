"""MCP (Model Context Protocol) tools integration.

This module provides integration with MCP servers, allowing the LangGraph agent
to connect to external tools and data sources via the MCP protocol.

Includes pre-configured MCP servers for:
- Web search (Brave, Tavily, DuckDuckGo)
- Filesystem access
- Fetch (HTTP requests)
- Memory (key-value storage)
"""

import os
from typing import Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.config import settings
from app.core.langgraph.state import MCPServerConfig
from app.core.logging import logger


class MCPToolManager:
    """Manager for MCP server connections and tool loading.

    This class handles the lifecycle of MCP server connections and provides
    tools that can be used by the LangGraph agent.
    """

    def __init__(self):
        """Initialize the MCP tool manager."""
        self._client: Optional[MultiServerMCPClient] = None
        self._tools: list[BaseTool] = []
        self._servers: dict[str, MCPServerConfig] = {}
        self._initialized = False

    def register_server(self, config: MCPServerConfig) -> None:
        """Register an MCP server configuration.

        Args:
            config: The MCP server configuration to register
        """
        if config.enabled:
            self._servers[config.name] = config
            logger.info("mcp_server_registered", server_name=config.name)

    def register_servers_from_config(self) -> None:
        """Register MCP servers from application configuration.

        Reads MCP server configurations from settings and registers them.
        """
        # Get MCP servers from environment/settings
        mcp_servers = getattr(settings, "MCP_SERVERS", [])

        for server_config in mcp_servers:
            if isinstance(server_config, dict):
                config = MCPServerConfig(**server_config)
            else:
                config = server_config
            self.register_server(config)

    async def initialize(self) -> list[BaseTool]:
        """Initialize MCP client and load tools from all registered servers.

        Returns:
            list[BaseTool]: List of tools loaded from MCP servers
        """
        if self._initialized:
            return self._tools

        if not self._servers:
            logger.info("no_mcp_servers_configured")
            self._initialized = True
            return []

        try:
            # Build server configurations for MultiServerMCPClient
            server_params = {}
            for name, config in self._servers.items():
                server_params[name] = {
                    "command": config.command,
                    "args": config.args,
                    "env": {**os.environ, **config.env},  # Merge with current env
                }

            # Create and initialize the client
            self._client = MultiServerMCPClient(server_params)
            await self._client.__aenter__()

            # Load tools from all servers
            self._tools = self._client.get_tools()

            logger.info(
                "mcp_tools_loaded",
                tool_count=len(self._tools),
                servers=list(self._servers.keys()),
            )

            self._initialized = True
            return self._tools

        except Exception as e:
            logger.error("mcp_initialization_failed", error=str(e))
            self._initialized = True
            return []

    async def cleanup(self) -> None:
        """Clean up MCP client connections."""
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
                logger.info("mcp_client_cleanup_complete")
            except Exception as e:
                logger.error("mcp_cleanup_error", error=str(e))
            finally:
                self._client = None
                self._tools = []
                self._initialized = False

    @property
    def tools(self) -> list[BaseTool]:
        """Get the loaded MCP tools.

        Returns:
            list[BaseTool]: The loaded MCP tools
        """
        return self._tools

    @property
    def is_initialized(self) -> bool:
        """Check if the MCP manager is initialized.

        Returns:
            bool: True if initialized
        """
        return self._initialized


# ============================================================================
# Pre-configured MCP Server Configs
# ============================================================================

def create_brave_search_mcp_config(
    api_key: Optional[str] = None,
    name: str = "brave-search",
) -> MCPServerConfig:
    """Create a configuration for the Brave Search MCP server.

    Brave Search provides high-quality web search results.
    Get your API key at: https://brave.com/search/api/

    Args:
        api_key: Brave Search API key (or set BRAVE_API_KEY env var)
        name: Name for this server configuration

    Returns:
        MCPServerConfig: Configuration for Brave Search MCP server
    """
    key = api_key or os.getenv("BRAVE_API_KEY", "")
    return MCPServerConfig(
        name=name,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env={"BRAVE_API_KEY": key} if key else {},
        enabled=bool(key),
    )


def create_tavily_search_mcp_config(
    api_key: Optional[str] = None,
    name: str = "tavily-search",
) -> MCPServerConfig:
    """Create a configuration for the Tavily Search MCP server.

    Tavily is an AI-optimized search engine.
    Get your API key at: https://tavily.com/

    Args:
        api_key: Tavily API key (or set TAVILY_API_KEY env var)
        name: Name for this server configuration

    Returns:
        MCPServerConfig: Configuration for Tavily Search MCP server
    """
    key = api_key or os.getenv("TAVILY_API_KEY", "")
    return MCPServerConfig(
        name=name,
        command="npx",
        args=["-y", "tavily-mcp@latest"],
        env={"TAVILY_API_KEY": key} if key else {},
        enabled=bool(key),
    )


def create_exa_search_mcp_config(
    api_key: Optional[str] = None,
    name: str = "exa-search",
) -> MCPServerConfig:
    """Create a configuration for the Exa Search MCP server.

    Exa provides semantic search for AI applications.
    Get your API key at: https://exa.ai/

    Args:
        api_key: Exa API key (or set EXA_API_KEY env var)
        name: Name for this server configuration

    Returns:
        MCPServerConfig: Configuration for Exa Search MCP server
    """
    key = api_key or os.getenv("EXA_API_KEY", "")
    return MCPServerConfig(
        name=name,
        command="npx",
        args=["-y", "@anthropic/mcp-server-exa"],
        env={"EXA_API_KEY": key} if key else {},
        enabled=bool(key),
    )


def create_filesystem_mcp_config(
    allowed_directories: list[str],
    name: str = "filesystem",
) -> MCPServerConfig:
    """Create a configuration for the filesystem MCP server.

    Provides file system access to specified directories.

    Args:
        allowed_directories: List of directories the server can access
        name: Name for this server configuration

    Returns:
        MCPServerConfig: Configuration for filesystem MCP server
    """
    return MCPServerConfig(
        name=name,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem"] + allowed_directories,
        enabled=True,
    )


def create_fetch_mcp_config(name: str = "fetch") -> MCPServerConfig:
    """Create a configuration for the fetch MCP server.

    Provides HTTP request capabilities for fetching web pages.

    Args:
        name: Name for this server configuration

    Returns:
        MCPServerConfig: Configuration for fetch MCP server
    """
    return MCPServerConfig(
        name=name,
        command="uvx",
        args=["mcp-server-fetch"],
        enabled=True,
    )


def create_memory_mcp_config(name: str = "memory") -> MCPServerConfig:
    """Create a configuration for the memory MCP server.

    Provides key-value memory storage for the agent.

    Args:
        name: Name for this server configuration

    Returns:
        MCPServerConfig: Configuration for memory MCP server
    """
    return MCPServerConfig(
        name=name,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
        enabled=True,
    )


def create_puppeteer_mcp_config(name: str = "puppeteer") -> MCPServerConfig:
    """Create a configuration for the Puppeteer MCP server.

    Provides browser automation and web scraping capabilities.

    Args:
        name: Name for this server configuration

    Returns:
        MCPServerConfig: Configuration for Puppeteer MCP server
    """
    return MCPServerConfig(
        name=name,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-puppeteer"],
        enabled=True,
    )


def get_default_search_mcp_configs() -> list[MCPServerConfig]:
    """Get default search MCP server configurations.

    Returns enabled configs based on available API keys.

    Returns:
        list[MCPServerConfig]: List of enabled search MCP configs
    """
    configs = []

    # Brave Search (if API key available)
    brave_config = create_brave_search_mcp_config()
    if brave_config.enabled:
        configs.append(brave_config)

    # Tavily Search (if API key available)
    tavily_config = create_tavily_search_mcp_config()
    if tavily_config.enabled:
        configs.append(tavily_config)

    # Exa Search (if API key available)
    exa_config = create_exa_search_mcp_config()
    if exa_config.enabled:
        configs.append(exa_config)

    # Always include fetch for basic web access
    configs.append(create_fetch_mcp_config())

    return configs


# Global MCP tool manager instance
mcp_manager = MCPToolManager()


def setup_default_mcp_servers() -> None:
    """Set up default MCP servers based on environment configuration.

    This registers search MCP servers based on available API keys.
    """
    # Register search servers based on available API keys
    for config in get_default_search_mcp_configs():
        mcp_manager.register_server(config)

    # Also register from settings if configured
    mcp_manager.register_servers_from_config()

    logger.info(
        "default_mcp_servers_setup",
        server_count=len(mcp_manager._servers),
        servers=list(mcp_manager._servers.keys()),
    )
