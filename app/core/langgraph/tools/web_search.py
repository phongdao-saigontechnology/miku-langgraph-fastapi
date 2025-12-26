"""Web Search tools for LangGraph.

This module provides comprehensive web search capabilities including:
- DuckDuckGo search (text, news, images)
- Tavily search (AI-optimized search)
- Custom search tool with configurable backends
"""

import os
from typing import Literal, Optional

from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.core.logging import logger


# ============================================================================
# DuckDuckGo Search Tools
# ============================================================================

class DuckDuckGoSearchInput(BaseModel):
    """Input schema for DuckDuckGo search."""

    query: str = Field(..., description="The search query to look up")
    max_results: int = Field(default=5, description="Maximum number of results to return (1-10)")


@tool(args_schema=DuckDuckGoSearchInput)
async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo.

    Use this tool to find current information from the internet.
    Good for: recent news, facts, definitions, how-to guides, current events.

    Args:
        query: The search query to look up
        max_results: Maximum number of results (1-10)

    Returns:
        Search results with titles, snippets, and URLs
    """
    try:
        max_results = min(max(1, max_results), 10)  # Clamp between 1-10

        wrapper = DuckDuckGoSearchAPIWrapper(
            max_results=max_results,
            time="m",  # Last month for freshness
        )

        results = wrapper.results(query, max_results=max_results)

        if not results:
            return f"No results found for: {query}"

        # Format results nicely
        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            snippet = result.get("snippet", result.get("body", "No description"))
            link = result.get("link", "")

            formatted.append(f"{i}. **{title}**\n   {snippet}\n   URL: {link}")

        logger.info("web_search_completed", query=query, result_count=len(results))

        return "\n\n".join(formatted)

    except Exception as e:
        logger.error("web_search_failed", query=query, error=str(e))
        return f"Search failed: {str(e)}"


class DuckDuckGoNewsInput(BaseModel):
    """Input schema for DuckDuckGo news search."""

    query: str = Field(..., description="The news topic to search for")
    max_results: int = Field(default=5, description="Maximum number of news articles (1-10)")


@tool(args_schema=DuckDuckGoNewsInput)
async def news_search(query: str, max_results: int = 5) -> str:
    """Search for recent news articles using DuckDuckGo.

    Use this tool to find current news and recent developments.
    Good for: breaking news, recent events, press releases, announcements.

    Args:
        query: The news topic to search for
        max_results: Maximum number of articles (1-10)

    Returns:
        News articles with titles, dates, and summaries
    """
    try:
        from ddgs import DDGS

        max_results = min(max(1, max_results), 10)

        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))

        if not results:
            return f"No news found for: {query}"

        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            body = result.get("body", "No description")
            date = result.get("date", "Unknown date")
            source = result.get("source", "Unknown source")
            url = result.get("url", "")

            formatted.append(
                f"{i}. **{title}**\n"
                f"   Source: {source} | Date: {date}\n"
                f"   {body[:200]}...\n"
                f"   URL: {url}"
            )

        logger.info("news_search_completed", query=query, result_count=len(results))

        return "\n\n".join(formatted)

    except Exception as e:
        logger.error("news_search_failed", query=query, error=str(e))
        return f"News search failed: {str(e)}"


# ============================================================================
# Tavily Search (AI-optimized search - requires API key)
# ============================================================================

class TavilySearchInput(BaseModel):
    """Input schema for Tavily search."""

    query: str = Field(..., description="The search query")
    search_depth: Literal["basic", "advanced"] = Field(
        default="basic",
        description="Search depth - 'basic' for quick results, 'advanced' for comprehensive research"
    )
    include_answer: bool = Field(
        default=True,
        description="Whether to include an AI-generated answer summary"
    )


def _get_tavily_tool() -> Optional[BaseTool]:
    """Get Tavily search tool if API key is configured.

    Returns:
        Tavily search tool or None if not configured
    """
    tavily_api_key = os.getenv("TAVILY_API_KEY")

    if not tavily_api_key:
        return None

    try:
        from langchain_community.tools.tavily_search import TavilySearchResults

        return TavilySearchResults(
            max_results=5,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
        )
    except ImportError:
        logger.warning("tavily_not_installed", message="Install tavily-python for Tavily search")
        return None
    except Exception as e:
        logger.error("tavily_init_failed", error=str(e))
        return None


# ============================================================================
# Combined Search Tool
# ============================================================================

class WebSearchInput(BaseModel):
    """Input schema for combined web search."""

    query: str = Field(..., description="The search query")
    search_type: Literal["web", "news"] = Field(
        default="web",
        description="Type of search - 'web' for general search, 'news' for recent news"
    )
    max_results: int = Field(default=5, description="Maximum results to return")


@tool(args_schema=WebSearchInput)
async def search(query: str, search_type: str = "web", max_results: int = 5) -> str:
    """Comprehensive web search tool.

    Use this tool to search the internet for information.

    Args:
        query: What to search for
        search_type: "web" for general search, "news" for recent news
        max_results: Number of results (1-10)

    Returns:
        Formatted search results
    """
    if search_type == "news":
        return await news_search(query, max_results)
    else:
        return await web_search(query, max_results)


# ============================================================================
# Tool Exports
# ============================================================================

def get_web_search_tools() -> list[BaseTool]:
    """Get all available web search tools.

    Returns:
        List of web search tools based on available configurations
    """
    tools = [
        web_search,
        news_search,
        search,
    ]

    # Add Tavily if configured
    tavily_tool = _get_tavily_tool()
    if tavily_tool:
        tools.append(tavily_tool)
        logger.info("tavily_search_enabled")

    return tools


# Default exports
web_search_tools = get_web_search_tools()

# Legacy compatibility - single search tool
duckduckgo_search_tool = DuckDuckGoSearchResults(
    num_results=10,
    handle_tool_error=True,
)

