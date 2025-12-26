"""Utility functions and main router setup for channels.

This module provides utilities for channel integrations including
JWT handling, session ID sanitization, and message processing.
"""

import re
from typing import Any, Dict, Optional

import jwt
from fastapi import APIRouter

from app.core.langgraph import LangGraphAgent
from app.core.logging import logger
from app.schemas import Message

# Global agent instance for channels - initialized lazily
_channel_agent: Optional[LangGraphAgent] = None


async def get_channel_agent() -> LangGraphAgent:
    """Get or create the channel agent instance.

    Returns:
        LangGraphAgent: The initialized agent
    """
    global _channel_agent

    if _channel_agent is None:
        _channel_agent = LangGraphAgent()
        await _channel_agent.initialize()
        logger.info("channel_agent_initialized")

    return _channel_agent


# Try to import BotFrameworkInput, but don't fail if dependencies are missing
try:
    from .bot_framework_input import BotFrameworkInput

    BOT_FRAMEWORK_AVAILABLE = True
except ImportError:
    BotFrameworkInput = None
    BOT_FRAMEWORK_AVAILABLE = False


def decode_jwt(bearer_token: str, jwt_key: str, jwt_algorithm: str) -> Dict[str, Any]:
    """Decode a Bearer Token using the specific JWT key and algorithm.

    Args:
        bearer_token: Encoded Bearer token
        jwt_key: Public JWT key for decoding the Bearer token
        jwt_algorithm: JWT algorithm used for decoding the Bearer token

    Returns:
        Dict containing the decoded payload if successful or raises exception
    """
    authorization_header_value = bearer_token.replace("Bearer ", "")
    return jwt.decode(authorization_header_value, jwt_key, algorithms=[jwt_algorithm])


def decode_bearer_token(
    bearer_token: str,
    jwt_key: str,
    jwt_algorithm: str,
) -> Optional[Dict[str, Any]]:
    """Decode a Bearer Token, returning None on failure.

    Args:
        bearer_token: Encoded Bearer token
        jwt_key: Public JWT key for decoding the Bearer token
        jwt_algorithm: JWT algorithm used for decoding the Bearer token

    Returns:
        Dict containing the decoded payload if successful or None if unsuccessful
    """
    try:
        return decode_jwt(bearer_token, jwt_key, jwt_algorithm)
    except jwt.exceptions.InvalidSignatureError:
        logger.error("jwt_invalid_signature")
    except Exception as e:
        logger.exception("jwt_decode_failed", error=str(e))

    return None


def _sanitize_session_id(raw_id: str) -> str:
    """Sanitize arbitrary sender IDs into a safe session_id.

    - If it's already UUID-like, keep as-is.
    - Otherwise, keep only [a-zA-Z0-9_-]; replace other chars with '-'.
    - Collapse multiple '-' and strip leading/trailing '-'.
    - Fallback to 'default' if empty after sanitization.

    Args:
        raw_id: The raw session/sender ID

    Returns:
        Sanitized session ID safe for use in database queries
    """
    if not isinstance(raw_id, str):
        raw_id = str(raw_id)

    # Replace disallowed characters
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", raw_id)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")

    return cleaned or "default"


async def on_new_message(
    channel_name: str = "",
    sender_id: str = "",
    text: str = "",
) -> Optional[str]:
    """Handle new messages from channels.

    This is the main entry point for processing messages from external channels
    like Bot Framework.

    Args:
        channel_name: Name of the channel (e.g., "botframework")
        sender_id: The sender's ID from the channel
        text: The message text

    Returns:
        The response text or None if processing failed
    """
    # Accept both raw text and objects with a `.text` attribute
    if not isinstance(text, str):
        text = getattr(text, "text", str(text))

    if not text.strip():
        logger.warning("empty_message_received", channel=channel_name, sender_id=sender_id)
        return None

    # Create message
    message = Message(role="user", content=text)

    # Sanitize session ID
    session_id = _sanitize_session_id(sender_id)

    try:
        # Get or initialize the agent
        agent = await get_channel_agent()

        # Get response
        result = await agent.get_response(
            messages=[message],
            session_id=session_id,
            user_id=sender_id,
        )

        # Extract response content
        if result:
            last_item = result[-1] if isinstance(result, list) else result

            if hasattr(last_item, "content"):
                return last_item.content
            elif isinstance(last_item, dict):
                return last_item.get("content")
            else:
                return str(last_item)

        return None

    except Exception as e:
        logger.error(
            "channel_message_processing_failed",
            channel=channel_name,
            sender_id=sender_id,
            error=str(e),
        )
        return f"Sorry, I encountered an error processing your message: {str(e)}"


def replace_synonyms(text: str, synonyms: Dict[str, list]) -> str:
    """Replace synonyms in text based on a dictionary of synonyms.

    Args:
        text: The input text
        synonyms: Dictionary where keys are target words and values are lists of synonyms

    Returns:
        Text with synonyms replaced
    """
    for target_word, synonym_list in synonyms.items():
        # Create a regex pattern to match any of the synonyms
        pattern = r"\b(" + "|".join(re.escape(s) for s in synonym_list) + r")\b"
        # Replace the synonyms with the target word
        text = re.sub(pattern, target_word, text, flags=re.IGNORECASE)
    return text


# Main router setup
routers = APIRouter(tags=["Channels"], prefix="/webhooks")

# Only set up BotFramework router if dependencies are available
if BOT_FRAMEWORK_AVAILABLE:
    input_channel = BotFrameworkInput()
    routers.include_router(input_channel.blueprint(on_new_message=on_new_message))
