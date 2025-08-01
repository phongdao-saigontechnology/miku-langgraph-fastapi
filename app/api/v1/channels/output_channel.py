"""
OutputChannel base class for handling output channels.
"""

import json
from typing import Text, Dict, Any


class OutputChannel:
    """Output channel base class.

    Provides sane implementation of the send methods
    for text only output channels.
    """

    @classmethod
    def name(cls) -> Text:
        """Every output channel needs a name to identify it."""
        return cls.__name__

    async def send_response(self, recipient_id: Text, message: Dict[Text, Any]) -> None:
        """Send a message to the client."""

        if message.get("text"):
            await self.send_text_message(recipient_id, message.pop("text"), **message)

        if message.get("custom"):
            await self.send_custom_json(recipient_id, message.pop("custom"), **message)

        # if there is an image we handle it separately as an attachment
        if message.get("image"):
            await self.send_image_url(recipient_id, message.pop("image"), **message)

        if message.get("attachment"):
            await self.send_attachment(recipient_id, message.pop("attachment"), **message)

    async def send_text_message(self, recipient_id: Text, text: Text, **kwargs: Any) -> None:
        """Send a message through this channel."""

        raise NotImplementedError("Output channel needs to implement a send message for simple texts.")

    async def send_image_url(self, recipient_id: Text, image: Text, **kwargs: Any) -> None:
        """Sends an image. Default will just post the url as a string."""

        await self.send_text_message(recipient_id, f"Image: {image}")

    async def send_attachment(self, recipient_id: Text, attachment: Text, **kwargs: Any) -> None:
        """Sends an attachment. Default will just post as a string."""

        await self.send_text_message(recipient_id, f"Attachment: {attachment}")

    async def send_custom_json(self, recipient_id: Text, json_message: Dict[Text, Any], **kwargs: Any) -> None:
        """Sends json dict to the output channel.

        Default implementation will just post the json contents as a string."""

        await self.send_text_message(recipient_id, json.dumps(json_message)) 