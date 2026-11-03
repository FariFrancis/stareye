import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from date.services import ChatAccessError, get_chat_match

from .models import MAX_MESSAGE_LENGTH, Message

# Close codes (4000-4999 are application-defined).
CLOSE_BAD_REQUEST = 4400
CLOSE_UNAUTHENTICATED = 4401
CLOSE_FORBIDDEN = 4403


class ChatConsumer(AsyncWebsocketConsumer):

    room_group_name = None

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        try:
            match_id = int(self.scope["url_route"]["kwargs"]["room_id"])
        except (KeyError, TypeError, ValueError):
            await self.close(code=CLOSE_BAD_REQUEST)
            return

        if not await self._can_chat(user, match_id):
            await self.close(code=CLOSE_FORBIDDEN)
            return

        self.user = user
        self.match_id = match_id
        self.room_group_name = f"chat_{match_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or "")
        except ValueError:
            await self._send_error("Invalid JSON")
            return

        text = data.get("message") if isinstance(data, dict) else None
        if not isinstance(text, str) or not text.strip():
            await self._send_error("Message content required")
            return
        text = text.strip()
        if len(text) > MAX_MESSAGE_LENGTH:
            await self._send_error(f"Message must be at most {MAX_MESSAGE_LENGTH} characters")
            return

        payload = await self._save_message(text)
        if payload is None:
            await self._send_error("Chat not available")
            await self.close(code=CLOSE_FORBIDDEN)
            return

        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", **payload}
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "id": event["id"],
            "message": event["message"],
            "sender": event["sender"],
            "timestamp": event["timestamp"],
        }))

    async def _send_error(self, message):
        await self.send(text_data=json.dumps({"error": message}))

    @database_sync_to_async
    def _can_chat(self, user, match_id):
        try:
            get_chat_match(user, match_id)
        except ChatAccessError:
            return False
        return True

    @database_sync_to_async
    def _save_message(self, text):
        try:
            match, me, _other = get_chat_match(self.user, self.match_id)
        except ChatAccessError:
            return None
        message = Message.objects.create(match=match, sending_user=me, message=text)
        return {
            "id": message.id,
            "message": message.message,
            "sender": me.user.username,
            "timestamp": message.creation_date.isoformat(),
        }