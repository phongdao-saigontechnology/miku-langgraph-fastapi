# Channels Package

This package contains the modular implementation of channel classes and utilities for handling different input and output channels.

## Structure

```
channels/
├── __init__.py              # Package initialization and exports
├── user_message.py          # UserMessage class
├── input_channel.py         # InputChannel base class
├── output_channel.py        # OutputChannel base class
├── collecting_output_channel.py  # CollectingOutputChannel implementation
├── bot_framework.py         # BotFramework output channel
├── bot_framework_input.py   # BotFrameworkInput implementation
├── utils.py                 # Utility functions and router setup
└── README.md               # This file
```

## Classes

### UserMessage
Represents an incoming message with channel information for responses.

**Location**: `user_message.py`

### InputChannel
Base class for input channels that handle incoming messages.

**Location**: `input_channel.py`

### OutputChannel
Base class for output channels that send messages to clients.

**Location**: `output_channel.py`

### CollectingOutputChannel
Output channel that collects messages in a list (for testing/debugging).

**Location**: `collecting_output_channel.py`

### BotFramework
Microsoft Bot Framework communication channel implementation.

**Location**: `bot_framework.py`

### BotFrameworkInput
Bot Framework input channel implementation with JWT validation.

**Location**: `bot_framework_input.py`

## Utilities

### Functions in utils.py
- `decode_jwt()`: Decodes JWT tokens
- `decode_bearer_token()`: Decodes bearer tokens with error handling
- `on_new_message()`: Handles new messages from channels
- `replace_synonyms()`: Replaces synonyms in text
- `routers`: Main FastAPI router setup

## Usage

The original `channel.py` file has been refactored to import from this modular structure, maintaining backward compatibility. All classes and functions are available through the main package import:

```python
from app.api.v1.channels import (
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
```

## Benefits of Modular Structure

1. **Separation of Concerns**: Each class has its own file
2. **Easier Maintenance**: Changes to one class don't affect others
3. **Better Testing**: Individual classes can be tested in isolation
4. **Improved Readability**: Smaller, focused files
5. **Reusability**: Classes can be imported individually as needed

## Migration

The original `channel.py` file now serves as a compatibility layer, importing and re-exporting all classes and functions from the new modular structure. This ensures that existing code continues to work without changes. 