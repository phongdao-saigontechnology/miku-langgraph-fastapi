"""
Legacy channel.py file - now imports from the modular channels package.
This file is kept for backward compatibility.
"""

# Import all classes and functions from the new modular structure
from .channels import (
    UserMessage,
    InputChannel,
    OutputChannel,
    CollectingOutputChannel,
    BotFramework,
    BotFrameworkInput,
    decode_jwt,
    decode_bearer_token,
    replace_synonyms,
    on_new_message,
    routers
)

# Re-export everything for backward compatibility
__all__ = [
    "UserMessage",
    "InputChannel",
    "OutputChannel", 
    "CollectingOutputChannel",
    "BotFramework",
    "BotFrameworkInput",
    "decode_jwt",
    "decode_bearer_token",
    "replace_synonyms",
    "on_new_message",
    "routers"
]
