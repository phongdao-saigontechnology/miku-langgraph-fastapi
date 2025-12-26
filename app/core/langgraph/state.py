"""Graph state definitions for LangGraph workflows.

This module defines the state schemas used throughout the LangGraph agent,
following the latest LangGraph v1.x patterns with Pydantic models.
"""

import re
import uuid
from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, field_validator


class AgentState(BaseModel):
    """State definition for the LangGraph Agent/Workflow.

    This state is passed between nodes in the graph and accumulates messages
    using the add_messages reducer for proper conversation history management.
    """

    messages: Annotated[list, add_messages] = Field(
        default_factory=list,
        description="The messages in the conversation, automatically accumulated",
    )
    session_id: str = Field(
        ...,
        description="The unique identifier for the conversation session",
    )
    # MCP-related state
    mcp_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context data from MCP servers",
    )
    # Tool execution tracking
    tool_calls_count: int = Field(
        default=0,
        description="Number of tool calls made in this conversation turn",
    )
    max_tool_calls: int = Field(
        default=10,
        description="Maximum tool calls allowed per turn to prevent infinite loops",
    )

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate that the session ID is a valid UUID or follows safe pattern.

        Args:
            v: The session ID to validate

        Returns:
            str: The validated session ID

        Raises:
            ValueError: If the session ID is not valid
        """
        # Try to validate as UUID
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            # If not a UUID, check for safe characters only
            if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
                raise ValueError(
                    "Session ID must contain only alphanumeric characters, underscores, and hyphens"
                )
            return v


class ToolCallResult(BaseModel):
    """Result from a tool execution."""

    tool_name: str
    tool_call_id: str
    result: Any
    success: bool = True
    error: Optional[str] = None


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server connection."""

    name: str = Field(..., description="Unique name for this MCP server")
    command: str = Field(..., description="Command to start the MCP server")
    args: list[str] = Field(default_factory=list, description="Arguments for the command")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    enabled: bool = Field(default=True, description="Whether this server is enabled")
    timeout: int = Field(default=30, description="Timeout in seconds for server operations")

