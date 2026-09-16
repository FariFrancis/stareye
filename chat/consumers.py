# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from chat.models import Message
from date.models import Match, UserProfile


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get("message")

        # Ensure user is authenticated
        user = self.scope["user"]
        if isinstance(user, AnonymousUser):
            return

        # Get sender profile
        sender_profile = UserProfile.objects.get(user=user)

        # Get match (room)
        match = Match.objects.get(id=self.room_id)

        # Save message to DB
        message_obj = Message.objects.create(
            match=match,
            sender=sender_profile,
            text=message_text
        )

        # Broadcast message to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_obj.text,
                "sender": sender_profile.user.username,
                "timestamp": message_obj.created_at.isoformat()
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender": event["sender"],
            "timestamp": event["timestamp"]
        }))
