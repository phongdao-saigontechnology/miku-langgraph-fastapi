"""
CollectingOutputChannel class for collecting messages in a list.
"""

from typing import Text, Dict, Any, List, Optional

from .output_channel import OutputChannel


class CollectingOutputChannel(OutputChannel):
    """Output channel that collects send messages in a list

    (doesn't send them anywhere, just collects them)."""

    def __init__(self) -> None:
        """Initialise list to collect messages."""
        self.messages: List[Dict[Text, Any]] = []

    @classmethod
    def name(cls) -> Text:
        """Name of the channel."""
        return "collector"

    @staticmethod
    def _message(
        recipient_id: Text,
        text: Text = None,
        image: Text = None,
        buttons: List[Dict[Text, Any]] = None,
        attachment: Text = None,
        custom: Dict[Text, Any] = None,
    ) -> Dict:
        """Create a message object that will be stored."""

        obj = {
            "recipient_id": recipient_id,
            "text": text,
            "image": image,
            "buttons": buttons,
            "attachment": attachment,
            "custom": custom,
        }

        # filter out any values that are `None`
        return {k: v for k, v in obj.items() if v is not None}

    def latest_output(self) -> Optional[Dict[Text, Any]]:
        if self.messages:
            return self.messages[-1]
        else:
            return None

    async def _persist_message(self, message: Dict[Text, Any]) -> None:
        self.messages.append(message)

    async def send_text_message(self, recipient_id: Text, text: Text, **kwargs: Any) -> None:
        for message_part in text.strip().split("\n\n"):
            await self._persist_message(self._message(recipient_id, text=message_part))

    async def send_image_url(self, recipient_id: Text, image: Text, **kwargs: Any) -> None:
        """Sends an image. Default will just post the url as a string."""

        await self._persist_message(self._message(recipient_id, image=image))

    async def send_attachment(self, recipient_id: Text, attachment: Text, **kwargs: Any) -> None:
        """Sends an attachment. Default will just post as a string."""

        await self._persist_message(self._message(recipient_id, attachment=attachment))

    async def send_text_with_buttons(
        self,
        recipient_id: Text,
        text: Text,
        buttons: List[Dict[Text, Any]],
        **kwargs: Any,
    ) -> None:
        await self._persist_message(self._message(recipient_id, text=text, buttons=buttons))

    async def send_custom_json(self, recipient_id: Text, json_message: Dict[Text, Any], **kwargs: Any) -> None:
        await self._persist_message(self._message(recipient_id, custom=json_message)) 