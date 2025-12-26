"""Graph builder for LangGraph workflows.

This module provides the graph builder that constructs the LangGraph workflow
using the latest v1.x patterns, including support for MCP tools and
PostgreSQL checkpointing.
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from psycopg_pool import AsyncConnectionPool

from app.core.config import Environment, settings
from app.core.langgraph.nodes import AgentNodes
from app.core.langgraph.state import AgentState
from app.core.logging import logger


class GraphBuilder:
    """Builder for constructing LangGraph workflows.

    This class follows the builder pattern to construct complex graphs
    with various configurations.
    """

    def __init__(self):
        """Initialize the graph builder."""
        self._llm: Optional[BaseChatModel] = None
        self._tools: list[BaseTool] = []
        self._checkpointer: Optional[AsyncPostgresSaver] = None
        self._connection_pool: Optional[AsyncConnectionPool] = None
        self._graph_name: str = f"{settings.PROJECT_NAME} Agent"

    def with_llm(self, llm: BaseChatModel) -> "GraphBuilder":
        """Set the LLM for the graph.

        Args:
            llm: The language model to use

        Returns:
            GraphBuilder: Self for chaining
        """
        self._llm = llm
        return self

    def with_tools(self, tools: list[BaseTool]) -> "GraphBuilder":
        """Set the tools for the graph.

        Args:
            tools: List of tools to use

        Returns:
            GraphBuilder: Self for chaining
        """
        self._tools = tools
        return self

    def with_name(self, name: str) -> "GraphBuilder":
        """Set the graph name.

        Args:
            name: Name for the graph

        Returns:
            GraphBuilder: Self for chaining
        """
        self._graph_name = name
        return self

    async def with_postgres_checkpointer(
        self,
        connection_string: Optional[str] = None,
        pool_size: Optional[int] = None,
    ) -> "GraphBuilder":
        """Configure PostgreSQL checkpointing.

        Args:
            connection_string: Database connection string (defaults to settings)
            pool_size: Connection pool size (defaults to settings)

        Returns:
            GraphBuilder: Self for chaining
        """
        conn_string = connection_string or settings.POSTGRES_URL
        max_size = pool_size or settings.POSTGRES_POOL_SIZE

        try:
            self._connection_pool = AsyncConnectionPool(
                conn_string,
                open=False,
                max_size=max_size,
                kwargs={
                    "autocommit": True,
                    "connect_timeout": 5,
                    "prepare_threshold": None,
                },
            )
            await self._connection_pool.open()

            self._checkpointer = AsyncPostgresSaver(self._connection_pool)
            await self._checkpointer.setup()

            logger.info(
                "checkpointer_configured",
                pool_size=max_size,
                environment=settings.ENVIRONMENT.value,
            )

        except Exception as e:
            logger.error("checkpointer_setup_failed", error=str(e))
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise
            # In production, continue without checkpointer
            self._checkpointer = None

        return self

    def build(self) -> CompiledStateGraph:
        """Build and compile the graph.

        Returns:
            CompiledStateGraph: The compiled graph ready for execution

        Raises:
            ValueError: If LLM is not configured
        """
        if self._llm is None:
            raise ValueError("LLM must be configured before building the graph")

        # Bind tools to LLM if any
        llm = self._llm
        if self._tools:
            llm = self._llm.bind_tools(self._tools)

        # Create tools lookup
        tools_by_name = {tool.name: tool for tool in self._tools}

        # Create nodes
        nodes = AgentNodes(llm=llm, tools_by_name=tools_by_name)

        # Build the graph
        graph_builder = StateGraph(AgentState)

        # Add nodes
        graph_builder.add_node("chat", nodes.chat_node)
        graph_builder.add_node("tools", nodes.tool_node)

        # Add edges
        graph_builder.set_entry_point("chat")
        graph_builder.add_conditional_edges(
            "chat",
            nodes.should_continue,
            {
                "tools": "tools",
                "end": END,
            },
        )
        graph_builder.add_edge("tools", "chat")

        # Compile with checkpointer if available
        compiled = graph_builder.compile(
            checkpointer=self._checkpointer,
            name=self._graph_name,
        )

        logger.info(
            "graph_built",
            graph_name=self._graph_name,
            tool_count=len(self._tools),
            has_checkpointer=self._checkpointer is not None,
            environment=settings.ENVIRONMENT.value,
        )

        return compiled

    @property
    def connection_pool(self) -> Optional[AsyncConnectionPool]:
        """Get the connection pool if configured.

        Returns:
            Optional[AsyncConnectionPool]: The connection pool
        """
        return self._connection_pool

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._connection_pool:
            await self._connection_pool.close()
            logger.info("connection_pool_closed")


async def create_default_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
    with_checkpointer: bool = True,
) -> tuple[CompiledStateGraph, GraphBuilder]:
    """Create a default graph with standard configuration.

    This is a convenience function for creating graphs with common settings.

    Args:
        llm: The language model to use
        tools: List of tools to use
        with_checkpointer: Whether to enable PostgreSQL checkpointing

    Returns:
        tuple: The compiled graph and the builder (for cleanup)
    """
    builder = GraphBuilder()
    builder.with_llm(llm).with_tools(tools)

    if with_checkpointer:
        await builder.with_postgres_checkpointer()

    graph = builder.build()

    return graph, builder

