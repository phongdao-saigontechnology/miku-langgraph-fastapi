"""
Channels package for handling different input and output channels.
"""

from .user_message import UserMessage
from .input_channel import InputChannel
from .output_channel import OutputChannel
from .collecting_output_channel import CollectingOutputChannel
from .utils import routers

# Try to import BotFramework classes, but don't fail if dependencies are missing
try:
    from .bot_framework import BotFramework
    from .bot_framework_input import BotFrameworkInput
    BOT_FRAMEWORK_AVAILABLE = True
except ImportError:
    # If JWT or other dependencies are missing, these won't be available
    BotFramework = None
    BotFrameworkInput = None
    BOT_FRAMEWORK_AVAILABLE = False

from .utils import decode_jwt, decode_bearer_token, replace_synonyms, on_new_message

__all__ = [
    "UserMessage",
    "InputChannel", 
    "OutputChannel",
    "CollectingOutputChannel",
    "decode_jwt",
    "decode_bearer_token",
    "replace_synonyms",
    "on_new_message",
    "routers",
]

# Add BotFramework classes to exports if available
if BOT_FRAMEWORK_AVAILABLE:
    __all__.extend(["BotFramework", "BotFrameworkInput"]) 