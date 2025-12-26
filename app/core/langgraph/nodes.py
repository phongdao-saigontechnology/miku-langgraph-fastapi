"""Graph nodes for LangGraph workflows.

This module defines the nodes (processing steps) used in the LangGraph agent,
following the latest LangGraph v1.x patterns.
"""

from typing import Any, Literal

from langchain_core.messages import ToolMessage
from langchain_core.language_models import BaseChatModel

from app.core.config import settings
from app.core.langgraph.state import AgentState
from app.core.logging import logger
from app.core.metrics import llm_inference_duration_seconds
from app.core.prompts import SYSTEM_PROMPT
from app.utils import dump_messages, prepare_messages


class AgentNodes:
    """Collection of nodes for the LangGraph agent.

    This class encapsulates all the node functions used in the graph,
    making it easier to test and maintain.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools_by_name: dict[str, Any],
    ):
        """Initialize the agent nodes.

        Args:
            llm: The language model to use for chat
            tools_by_name: Dictionary mapping tool names to tool instances
        """
        self.llm = llm
        self.tools_by_name = tools_by_name

    async def chat_node(self, state: AgentState) -> dict:
        """Process the chat state and generate a response.

        This node handles the main LLM interaction, including retry logic
        and metrics tracking.

        Args:
            state: The current agent state

        Returns:
            dict: Updated state with new messages
        """
        messages = prepare_messages(state.messages, self.llm, SYSTEM_PROMPT)
        max_retries = settings.MAX_LLM_CALL_RETRIES

        for attempt in range(max_retries):
            try:
                # Get model name for metrics
                model_name = getattr(self.llm, "model", getattr(self.llm, "model_name", settings.LLM_MODEL))

                with llm_inference_duration_seconds.labels(model=model_name).time():
                    response = await self.llm.ainvoke(dump_messages(messages))

                logger.info(
                    "llm_response_generated",
                    session_id=state.session_id,
                    attempt=attempt + 1,
                    model=model_name,
                    has_tool_calls=bool(getattr(response, "tool_calls", None)),
                )

                return {"messages": [response]}

            except Exception as e:
                logger.error(
                    "llm_call_failed",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                    session_id=state.session_id,
                )

                if attempt == max_retries - 1:
                    raise Exception(f"Failed to get LLM response after {max_retries} attempts: {e}")

                continue

        raise Exception(f"Failed to get LLM response after {max_retries} attempts")

    async def tool_node(self, state: AgentState) -> dict:
        """Execute tool calls from the last message.

        This node processes tool calls made by the LLM and returns
        the results as ToolMessage objects.

        Args:
            state: The current agent state with pending tool calls

        Returns:
            dict: Updated state with tool results
        """
        outputs = []
        last_message = state.messages[-1]

        # Check for tool call limit
        current_count = state.tool_calls_count
        max_calls = state.max_tool_calls

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            logger.warning("tool_node_called_without_tool_calls", session_id=state.session_id)
            return {"messages": []}

        for tool_call in last_message.tool_calls:
            # Check tool call limit
            if current_count >= max_calls:
                logger.warning(
                    "tool_call_limit_reached",
                    session_id=state.session_id,
                    limit=max_calls,
                )
                outputs.append(
                    ToolMessage(
                        content=f"Tool call limit ({max_calls}) reached. Please provide a response.",
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )
                continue

            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            try:
                if tool_name not in self.tools_by_name:
                    error_msg = f"Tool '{tool_name}' not found"
                    logger.error("tool_not_found", tool_name=tool_name, session_id=state.session_id)
                    outputs.append(
                        ToolMessage(
                            content=error_msg,
                            name=tool_name,
                            tool_call_id=tool_call["id"],
                        )
                    )
                    continue

                # Execute the tool
                tool = self.tools_by_name[tool_name]
                result = await tool.ainvoke(tool_args)

                logger.info(
                    "tool_executed",
                    tool_name=tool_name,
                    session_id=state.session_id,
                )

                outputs.append(
                    ToolMessage(
                        content=str(result) if result else "Tool executed successfully",
                        name=tool_name,
                        tool_call_id=tool_call["id"],
                    )
                )
                current_count += 1

            except Exception as e:
                logger.error(
                    "tool_execution_failed",
                    tool_name=tool_name,
                    error=str(e),
                    session_id=state.session_id,
                )
                outputs.append(
                    ToolMessage(
                        content=f"Error executing {tool_name}: {str(e)}",
                        name=tool_name,
                        tool_call_id=tool_call["id"],
                    )
                )

        return {
            "messages": outputs,
            "tool_calls_count": current_count,
        }

    def should_continue(self, state: AgentState) -> Literal["tools", "end"]:
        """Determine if the agent should continue to tools or end.

        Args:
            state: The current agent state

        Returns:
            Literal["tools", "end"]: Next node to route to
        """
        if not state.messages:
            return "end"

        last_message = state.messages[-1]

        # Check if we've hit the tool call limit
        if state.tool_calls_count >= state.max_tool_calls:
            logger.info(
                "routing_to_end_tool_limit",
                session_id=state.session_id,
                tool_calls_count=state.tool_calls_count,
            )
            return "end"

        # Check if the last message has tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        return "end"

