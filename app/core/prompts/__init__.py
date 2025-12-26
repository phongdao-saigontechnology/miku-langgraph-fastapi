"""System prompts for the Miku AI agent."""

import os
from datetime import datetime


def load_system_prompt() -> str:
    """Load and format the system prompt from the file.

    Returns:
        str: The formatted system prompt with current date/time
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "system.md")

    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    return template.format(
        current_date_and_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


# Load the system prompt on module import
SYSTEM_PROMPT = load_system_prompt()

__all__ = ["SYSTEM_PROMPT", "load_system_prompt"]
