"""
Utility functions and main router setup for channels.
"""

import re
from typing import Dict, Any, Optional

import jwt
from fastapi import APIRouter

from langchain_core.messages import HumanMessage
from app.core.langgraph.graph import LangGraphAgent


agent = LangGraphAgent()
# Try to import BotFrameworkInput, but don't fail if dependencies are missing
try:
    from .bot_framework_input import BotFrameworkInput
    BOT_FRAMEWORK_AVAILABLE = True
except ImportError:
    BotFrameworkInput = None
    BOT_FRAMEWORK_AVAILABLE = False


def decode_jwt(bearer_token: str, jwt_key: str, jwt_algorithm: str) -> Dict:
    """Decodes a Bearer Token using the specific JWT key and algorithm.

    Args:
        bearer_token: Encoded Bearer token
        jwt_key: Public JWT key for decoding the Bearer token
        jwt_algorithm: JWT algorithm used for decoding the Bearer token

    Returns:
        `Dict` containing the decoded payload if successful or an exception
        if unsuccessful
    """
    authorization_header_value = bearer_token.replace("Bearer ", "")
    return jwt.decode(authorization_header_value, jwt_key, algorithms=jwt_algorithm)


def decode_bearer_token(bearer_token: str, jwt_key: str, jwt_algorithm: str) -> Optional[Dict]:
    """Decodes a Bearer Token using the specific JWT key and algorithm.

    Args:
        bearer_token: Encoded Bearer token
        jwt_key: Public JWT key for decoding the Bearer token
        jwt_algorithm: JWT algorithm used for decoding the Bearer token

    Returns:
        `Dict` containing the decoded payload if successful or `None` if unsuccessful
    """
    # noinspection PyBroadException
    try:
        return decode_jwt(bearer_token, jwt_key, jwt_algorithm)
    except jwt.exceptions.InvalidSignatureError:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("JWT public key invalid.")
    except Exception:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Failed to decode bearer token.")

    return None


async def on_new_message(channel_name="", sender_id="", text=""):
    """Handle new messages from channels."""
    message = HumanMessage(content=text, role="user")
    state = {
        "messages": [message],
        "initial_search_query_count": 1,
        "max_research_loops": 1,
        "reasoning_model": "gemini-2.5-flash",
    }

    result = await agent.get_response(
        [message], sender_id, user_id=sender_id
    )

    if result:
        response = result[-1].get("content") if isinstance(result, list) else result[-1].content
    return response


def replace_synonyms(text: str, synonyms: Dict[str, list]) -> str:
    """
    Replaces synonyms in a given text based on a dictionary of synonyms.
    Args:
        text (str): The input text.
        synonyms (dict): A dictionary where keys are the target words and values are lists of synonyms.

    Returns:
        str: The text with synonyms replaced.
    """
    for target_word, synonym_list in synonyms.items():
        # Create a regex pattern to match any of the synonyms
        pattern = r"\b(" + "|".join(synonym_list) + r")\b"
        # Replace the synonyms with the target word
        text = re.sub(pattern, target_word, text, flags=re.IGNORECASE)
    return text


# Main router setup
routers = APIRouter(tags=["Channels"], prefix="/webhooks")

# Only set up BotFramework router if dependencies are available
if BOT_FRAMEWORK_AVAILABLE:
    input_channel = BotFrameworkInput()
    routers.include_router(input_channel.blueprint(on_new_message=on_new_message)) 