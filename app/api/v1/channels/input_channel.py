"""
InputChannel base class for handling input channels.
"""

from typing import Text, Dict, Any, Optional, Callable, Awaitable

from fastapi import Request


class InputChannel:
    """Input channel base class."""

    @classmethod
    def name(cls) -> Text:
        """Every input channel needs a name to identify it."""
        return cls.__name__

    def url_prefix(self) -> Text:
        return self.name()

    def blueprint(self, on_new_message: Callable[["UserMessage"], Awaitable[Any]]) -> "APIRouter":
        """Defines a FastAPI API router.

        The blueprint will be attached to a running server and handle
        incoming routes it registered for."""
        raise NotImplementedError("Component listener needs to provide blueprint.")

    def get_output_channel(self) -> Optional["OutputChannel"]:
        """Create ``OutputChannel`` based on information provided by the input channel.

        Implementing this function is not required. If this function returns a valid
        ``OutputChannel`` this can be used by Rasa to send bot responses to the user
        without the user initiating an interaction.

        Returns:
            ``OutputChannel`` instance or ``None`` in case creating an output channel
             only based on the information present in the ``InputChannel`` is not
             possible.
        """
        pass

    def get_metadata(self, request: Request) -> Optional[Dict[Text, Any]]:
        """Extracts additional information from the incoming request.

         Implementing this function is not required. However, it can be used to extract
         metadata from the request. The return value is passed on to the
         ``UserMessage`` object and stored in the conversation tracker.

        Args:
            request: incoming request with the message of the user

        Returns:
            Metadata which was extracted from the request.
        """
        pass 