"""Graph schema for the application.

This module provides backward compatibility by re-exporting the state
definitions from the refactored langgraph.state module.
"""

# Re-export from the new location for backward compatibility
from app.core.langgraph.state import (
    AgentState,
    AgentState as GraphState,  # Alias for backward compatibility
    MCPServerConfig,
    ToolCallResult,
)

__all__ = [
    "GraphState",
    "AgentState",
    "MCPServerConfig",
    "ToolCallResult",
]
