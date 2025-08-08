"""
BotFrameworkInput class for Bot Framework input channel implementation.
"""

import datetime
import logging
import os
import re
from typing import Text, Dict, Any, Optional

import jwt
import requests
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from jwt import InvalidKeyError, PyJWTError
from jwt.algorithms import RSAAlgorithm
from requests import HTTPError

from .input_channel import InputChannel
from .user_message import UserMessage
from .bot_framework import BotFramework

logger = logging.getLogger(__name__)

MICROSOFT_OPEN_ID_URI = "https://login.botframework.com/v1/.well-known/openidconfiguration"
BEARER_REGEX = re.compile(r"Bearer\s+(.*)")


class BotFrameworkInput(InputChannel):
    """Bot Framework input channel implementation."""

    @classmethod
    def name(cls) -> Text:
        return "botframework"

    def __init__(self) -> None:
        """Create a Bot Framework input channel.

        Args:

        """
        self.app_id = os.environ.get("APP_ID")
        self.app_password = os.environ.get("APP_PASSWORD")

        self.jwt_keys: Dict[Text, Any] = {}
        self.jwt_update_time = datetime.datetime.fromtimestamp(0)

        self._update_cached_jwk_keys()

    def _update_cached_jwk_keys(self) -> None:
        logger.debug("Updating JWT keys for the Botframework.")
        response = requests.get(MICROSOFT_OPEN_ID_URI)
        response.raise_for_status()
        conf = response.json()

        jwks_uri = conf["jwks_uri"]

        keys_request = requests.get(jwks_uri)
        keys_request.raise_for_status()
        keys_list = keys_request.json()
        self.jwt_keys = {key["kid"]: key for key in keys_list["keys"]}
        self.jwt_update_time = datetime.datetime.now()

    def _validate_jwt_token(self, jwt_token: Text) -> None:
        jwt_header = jwt.get_unverified_header(jwt_token)
        key_id = jwt_header["kid"]
        if key_id not in self.jwt_keys:
            raise InvalidKeyError(f"JWT Key with ID {key_id} not found.")

        key_json = self.jwt_keys[key_id]
        public_key = RSAAlgorithm.from_jwk(key_json)
        jwt.decode(
            jwt_token,
            key=public_key,
            audience=self.app_id,
            algorithms=jwt_header["alg"],
        )

    def _validate_auth(self, auth_header: Optional[Text]) -> Optional[JSONResponse]:
        if not auth_header:
            return JSONResponse("No authorization header provided.", status_code=status.HTTP_401_UNAUTHORIZED)

        # Update the JWT keys daily
        if datetime.datetime.now() - self.jwt_update_time > datetime.timedelta(days=1):
            try:
                self._update_cached_jwk_keys()
            except HTTPError as error:
                logger.warning(f"Could not update JWT keys from {MICROSOFT_OPEN_ID_URI}.")
                logger.exception(error, exc_info=True)

        auth_match = BEARER_REGEX.match(auth_header)
        if not auth_match:
            return JSONResponse(
                "No Bearer token provided in Authorization header.", status_code=status.HTTP_401_UNAUTHORIZED
            )

        (jwt_token,) = auth_match.groups()

        try:
            self._validate_jwt_token(jwt_token)
        except PyJWTError as error:
            logger.error("Bot framework JWT token could not be verified.")
            logger.exception(error, exc_info=True)
            return JSONResponse("Could not validate JWT token.", status_code=status.HTTP_401_UNAUTHORIZED)

        return None

    @staticmethod
    def add_attachments_to_metadata(
        postdata: Dict[Text, Any], metadata: Optional[Dict[Text, Any]]
    ) -> Optional[Dict[Text, Any]]:
        """Merge the values of `postdata['attachments']` with `metadata`."""
        if postdata.get("attachments"):
            attachments = {"attachments": postdata["attachments"]}
            if metadata:
                metadata.update(attachments)
            else:
                metadata = attachments
        return metadata

    def blueprint(self, on_new_message) -> APIRouter:
        """Defines the FastAPI blueprint for the bot framework integration."""
        botframework_webhook = APIRouter(prefix="/botframework_webhook")

        @botframework_webhook.get("/")
        async def health(request: Request) -> JSONResponse:
            return JSONResponse({"status": "ok"})

        @botframework_webhook.post("/webhook")
        async def webhook(request: Request) -> JSONResponse:
            validation_response = self._validate_auth(request.headers.get("Authorization"))
            if validation_response:
                return validation_response

            postdata = await request.json()
            metadata = self.get_metadata(request)

            metadata_with_attachments = self.add_attachments_to_metadata(postdata, metadata)

            try:
                if postdata["type"] == "message":
                    out_channel = BotFramework(
                        self.app_id,
                        self.app_password,
                        postdata["conversation"],
                        postdata["recipient"],
                        postdata["serviceUrl"],
                    )

                    user_msg = UserMessage(
                        text=postdata.get("text", ""),
                        output_channel=out_channel,
                        sender_id=postdata["from"]["id"],
                        input_channel=self.name(),
                        metadata=metadata_with_attachments,
                    )

                    await on_new_message(sender_id=postdata["from"]["id"], text=user_msg)
                else:
                    logger.info("Not received message type")
            except Exception as e:
                logger.error(f"Exception when trying to handle message.{e}")
                logger.debug(e, exc_info=True)
                pass

            return JSONResponse(content="success")

        return botframework_webhook 