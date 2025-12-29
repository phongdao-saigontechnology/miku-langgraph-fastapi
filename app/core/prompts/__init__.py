"""System prompts for the Miku AI agent."""

import os
from datetime import datetime, timezone, timedelta


# UTC+7 timezone (Vietnam, Thailand, Indonesia WIB)
UTC_PLUS_7 = timezone(timedelta(hours=7))


def load_system_prompt() -> str:
    """Load and format the system prompt from the file.

    Returns:
        str: The formatted system prompt with current date/time in UTC+7
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "system.md")

    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Get current time in UTC+7
    current_time = datetime.now(UTC_PLUS_7)

    return template.format(
        current_date_and_time=current_time.strftime("%Y-%m-%d %H:%M:%S"),
    )


__all__ = ["load_system_prompt"]
