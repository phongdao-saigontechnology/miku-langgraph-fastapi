"""LangGraph Agent - Main agent interface.

This module provides the main LangGraph Agent class that serves as the
primary interface for interacting with the LangGraph workflow. It supports
both regular and streaming responses, MCP tool integration, and conversation
history management.
"""

import uuid
from typing import AsyncGenerator, Optional

from asgiref.sync import sync_to_async
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, convert_to_openai_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot

from app.core.config import Environment, settings
from app.core.langgraph.builder import GraphBuilder
from app.core.langgraph.state import MCPServerConfig
from app.core.langgraph.tools import get_all_tools, mcp_manager, builtin_tools
from app.core.logging import logger
from app.core.metrics import llm_stream_duration_seconds
from app.schemas import Message
from app.utils import dump_messages


class LangGraphAgent:
    """Main LangGraph Agent for handling conversations.

    This class provides a high-level interface for:
    - Chat completions (regular and streaming)
    - Conversation history management
    - MCP server integration
    - Tool execution
    """

    def __init__(self):
        """Initialize the LangGraph Agent."""
        self._graph: Optional[CompiledStateGraph] = None
        self._builder: Optional[GraphBuilder] = None
        self._initialized = False

        # Initialize LLM
        self.llm = self._create_llm()

        logger.info(
            "agent_initialized",
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            environment=settings.ENVIRONMENT.value,
        )

    def _create_llm(self) -> BaseChatModel:
        """Create the LLM instance based on configured provider.

        Supports multiple LLM providers:
        - openai: OpenAI GPT models (gpt-4o-mini, gpt-4o, etc.)
        - google: Google Gemini models (gemini-1.5-flash, gemini-1.5-pro, etc.)
        - mistral: Mistral AI models (mistral-small-latest, mistral-large-latest, etc.)

        Returns:
            BaseChatModel: Configured LLM instance for the selected provider
        """
        provider = settings.LLM_PROVIDER
        model_kwargs = self._get_model_kwargs()

        logger.info(
            "creating_llm",
            provider=provider,
            model=settings.LLM_MODEL,
        )

        if provider == "mistral":
            return self._create_mistral_llm(model_kwargs)
        elif provider == "google":
            return self._create_google_llm(model_kwargs)
        else:
            # Default to OpenAI
            return self._create_openai_llm(model_kwargs)

    def _create_mistral_llm(self, model_kwargs: dict) -> ChatMistralAI:
        """Create a Mistral AI LLM instance.

        Args:
            model_kwargs: Additional model configuration

        Returns:
            ChatMistralAI: Configured Mistral LLM instance
        """
        return ChatMistralAI(
            model=settings.LLM_MODEL,
            temperature=settings.DEFAULT_LLM_TEMPERATURE,
            api_key=settings.MISTRAL_API_KEY,
            max_tokens=settings.MAX_TOKENS,
            **model_kwargs,
        )

    def _create_openai_llm(self, model_kwargs: dict) -> ChatOpenAI:
        """Create an OpenAI LLM instance.

        Args:
            model_kwargs: Additional model configuration

        Returns:
            ChatOpenAI: Configured OpenAI LLM instance
        """
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.DEFAULT_LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            max_tokens=settings.MAX_TOKENS,
            **model_kwargs,
        )

    def _create_google_llm(self, model_kwargs: dict) -> ChatGoogleGenerativeAI:
        """Create a Google Gemini LLM instance.

        Args:
            model_kwargs: Additional model configuration

        Returns:
            ChatGoogleGenerativeAI: Configured Google LLM instance
        """
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            temperature=settings.DEFAULT_LLM_TEMPERATURE,
            api_key=settings.GOOGLE_API_KEY,
            max_tokens=settings.MAX_TOKENS,
            **model_kwargs,
        )

    def _get_model_kwargs(self) -> dict:
        """Get environment-specific model kwargs.

        Returns:
            dict: Model configuration based on environment
        """
        kwargs = {}

        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            kwargs["top_p"] = 0.8
        elif settings.ENVIRONMENT == Environment.PRODUCTION:
            kwargs["top_p"] = 0.95

        return kwargs

    def register_mcp_server(self, config: MCPServerConfig) -> None:
        """Register an MCP server for tool integration.

        Args:
            config: MCP server configuration
        """
        mcp_manager.register_server(config)
        logger.info("mcp_server_registered_to_agent", server_name=config.name)

    async def initialize(self) -> None:
        """Initialize the agent and create the graph.

        This method should be called before using the agent. It sets up
        the graph with all configured tools including MCP tools.
        """
        if self._initialized:
            return

        try:
            # Get all tools including MCP tools
            all_tools = await get_all_tools()

            logger.info(
                "tools_loaded",
                total_tools=len(all_tools),
                builtin_tools=len(builtin_tools),
                mcp_tools=len(all_tools) - len(builtin_tools),
            )

            # Build the graph
            self._builder = GraphBuilder()
            self._builder.with_llm(self.llm).with_tools(all_tools)

            # Configure checkpointer
            await self._builder.with_postgres_checkpointer()

            # Build the graph
            self._graph = self._builder.build()

            self._initialized = True

            logger.info(
                "agent_ready",
                environment=settings.ENVIRONMENT.value,
                has_checkpointer=self._builder._checkpointer is not None,
            )

        except Exception as e:
            logger.error("agent_initialization_failed", error=str(e))
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise
            # In production, create a minimal graph without checkpointer
            self._builder = GraphBuilder()
            self._builder.with_llm(self.llm).with_tools(builtin_tools)
            self._graph = self._builder.build()
            self._initialized = True

    async def _ensure_initialized(self) -> None:
        """Ensure the agent is initialized."""
        if not self._initialized:
            await self.initialize()

    def _get_config(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """Create configuration for graph invocation.

        Args:
            session_id: The session ID for the conversation
            user_id: Optional user ID for tracking

        Returns:
            dict: Configuration for graph invocation
        """
        # Build callbacks list - only add Langfuse if configured
        callbacks = []
        if settings.LANGFUSE_PUBLIC_KEY:
            # Generate a valid trace_id (32 lowercase hex chars)
            trace_id = uuid.uuid4().hex
            trace_context = {
                "trace_id": trace_id,
                "metadata": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "environment": settings.ENVIRONMENT.value,
                },
            }
            callbacks.append(CallbackHandler(trace_context=trace_context))

        return {
            "configurable": {"thread_id": session_id},
            "callbacks": callbacks,
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "environment": settings.ENVIRONMENT.value,
            },
        }

    async def get_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
    ) -> list[Message]:
        """Get a response from the agent.

        Args:
            messages: The messages to send to the agent
            session_id: The session ID for the conversation
            user_id: Optional user ID for tracking

        Returns:
            list[Message]: The response messages
        """
        await self._ensure_initialized()

        config = self._get_config(session_id, user_id)

        try:
            response = await self._graph.ainvoke(
                {
                    "messages": dump_messages(messages),
                    "session_id": session_id,
                },
                config,
            )

            return self._process_messages(response["messages"])

        except Exception as e:
            logger.error(
                "agent_response_error",
                session_id=session_id,
                error=str(e),
            )
            raise

    async def get_stream_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Get a streaming response from the agent.

        Args:
            messages: The messages to send to the agent
            session_id: The session ID for the conversation
            user_id: Optional user ID for tracking

        Yields:
            str: Response tokens as they're generated
        """
        await self._ensure_initialized()

        config = self._get_config(session_id, user_id)
        model_name = getattr(self.llm, "model", settings.LLM_MODEL)

        try:
            with llm_stream_duration_seconds.labels(model=model_name).time():
                async for event in self._graph.astream_events(
                    {
                        "messages": dump_messages(messages),
                        "session_id": session_id,
                    },
                    config,
                    version="v2",
                ):
                    # Handle different event types
                    kind = event.get("event")

                    if kind == "on_chat_model_stream":
                        content = event.get("data", {}).get("chunk", {})
                        if hasattr(content, "content") and content.content:
                            yield content.content

        except Exception as e:
            logger.error(
                "agent_stream_error",
                session_id=session_id,
                error=str(e),
            )
            raise

    async def get_chat_history(self, session_id: str) -> list[Message]:
        """Get the chat history for a session.

        Args:
            session_id: The session ID to retrieve history for

        Returns:
            list[Message]: The chat history
        """
        await self._ensure_initialized()

        try:
            state: StateSnapshot = await sync_to_async(self._graph.get_state)(
                config={"configurable": {"thread_id": session_id}}
            )

            if state.values:
                return self._process_messages(state.values.get("messages", []))
            return []

        except Exception as e:
            logger.error(
                "chat_history_error",
                session_id=session_id,
                error=str(e),
            )
            return []

    async def clear_chat_history(self, session_id: str) -> None:
        """Clear the chat history for a session.

        Args:
            session_id: The session ID to clear history for
        """
        await self._ensure_initialized()

        if self._builder and self._builder.connection_pool:
            try:
                async with self._builder.connection_pool.connection() as conn:
                    for table in settings.CHECKPOINT_TABLES:
                        await conn.execute(
                            f"DELETE FROM {table} WHERE thread_id = %s",
                            (session_id,),
                        )
                        logger.info(f"cleared_{table}", session_id=session_id)

            except Exception as e:
                logger.error(
                    "clear_history_error",
                    session_id=session_id,
                    error=str(e),
                )
                raise

    def _process_messages(self, messages: list[BaseMessage]) -> list[Message]:
        """Process LangChain messages to API format.

        Args:
            messages: LangChain message objects

        Returns:
            list[Message]: Processed messages in API format
        """
        openai_style = convert_to_openai_messages(messages)

        return [
            Message(**msg)
            for msg in openai_style
            if msg.get("role") in ["assistant", "user"] and msg.get("content")
        ]

    async def cleanup(self) -> None:
        """Clean up agent resources."""
        if self._builder:
            await self._builder.cleanup()

        await mcp_manager.cleanup()

        logger.info("agent_cleanup_complete")


# Backward compatibility - keep the old class name
# This allows existing code to continue working
LangGraphAgent = LangGraphAgent

