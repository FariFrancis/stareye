from django.test import TestCase

# Create your tests here.
import json

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from date import services
from date.testing import make_user

from .consumers import ChatConsumer
from .models import MAX_MESSAGE_LENGTH, Message


def accepted_match(a_profile, b_profile):
    match, _ = services.request_match(a_profile, b_profile)
    return services.respond_to_match(b_profile, match.id, accept=True)


@override_settings(ENABLE_EMBEDDINGS=False)
class ChatRestTests(TestCase):
    def setUp(self):
        self.alice_user, self.alice = make_user("alice", gender="f")
        self.bob_user, self.bob = make_user("bob", gender="m")
        self.eve_user, self.eve = make_user("eve", gender="f")
        self.match = accepted_match(self.alice, self.bob)

    def send(self, user, text="hi", match=None):
        self.client.force_login(user)
        url = reverse("send-message", args=[(match or self.match).id])
        return self.client.post(url, data=json.dumps({"message": text}),
                                content_type="application/json")

    def test_participants_can_send_and_read(self):
        self.assertEqual(self.send(self.alice_user, "hello").status_code, 201)
        self.client.force_login(self.bob_user)
        response = self.client.get(reverse("get-message", args=[self.match.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["messages"][0]["message"], "hello")

    def test_outsiders_cannot_read_or_send(self):
        self.assertEqual(self.send(self.eve_user).status_code, 403)
        self.client.force_login(self.eve_user)
        response = self.client.get(reverse("get-message", args=[self.match.id]))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_users_are_redirected_to_login(self):
        response = self.client.get(reverse("get-message", args=[self.match.id]))
        self.assertEqual(response.status_code, 302)

    def test_pending_matches_cannot_chat(self):
        pending, _ = services.request_match(self.alice, self.eve)
        self.assertEqual(self.send(self.alice_user, match=pending).status_code, 403)

    def test_blocking_ends_the_chat(self):
        services.block_user(self.bob, self.alice)
        self.assertEqual(self.send(self.alice_user).status_code, 403)

    def test_validation(self):
        self.client.force_login(self.alice_user)
        url = reverse("send-message", args=[self.match.id])
        bad_json = self.client.post(url, data="not json", content_type="application/json")
        self.assertEqual(bad_json.status_code, 400)
        self.assertEqual(self.send(self.alice_user, "   ").status_code, 400)
        self.assertEqual(self.send(self.alice_user, "x" * (MAX_MESSAGE_LENGTH + 1)).status_code, 400)

    def test_only_sender_can_delete(self):
        self.send(self.alice_user, "oops")
        message = Message.objects.get()
        url = reverse("delete-message", args=[message.id])

        self.client.force_login(self.bob_user)
        self.assertEqual(self.client.patch(url).status_code, 403)

        self.client.force_login(self.alice_user)
        self.assertEqual(self.client.patch(url).status_code, 200)
        message.refresh_from_db()
        self.assertTrue(message.is_deleted)
        self.assertIsNotNone(message.deleted_at)

    def test_history_pagination(self):
        for i in range(5):
            Message.objects.create(match=self.match, sending_user=self.alice, message=f"m{i}")
        self.client.force_login(self.alice_user)
        data = self.client.get(reverse("get-message", args=[self.match.id]) + "?limit=2").json()
        self.assertEqual([m["message"] for m in data["messages"]], ["m3", "m4"])
        self.assertTrue(data["has_more"])

    def test_room_page_requires_access(self):
        self.client.force_login(self.eve_user)
        self.assertEqual(self.client.get(reverse("chat-room", args=[self.match.id])).status_code, 404)
        self.client.force_login(self.alice_user)
        self.assertEqual(self.client.get(reverse("chat-room", args=[self.match.id])).status_code, 200)


@override_settings(ENABLE_EMBEDDINGS=False)
class ChatConsumerTests(TransactionTestCase):
    def setUp(self):
        self.alice_user, self.alice = make_user("alice", gender="f")
        self.bob_user, self.bob = make_user("bob", gender="m")
        self.eve_user, self.eve = make_user("eve", gender="f")
        self.match = accepted_match(self.alice, self.bob)

    def communicator(self, user):
        comm = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.match.pk}/")
        comm.scope["user"] = user
        comm.scope["url_route"] = {"kwargs": {"room_id": self.match.pk}}
        return comm

    async def test_anonymous_is_rejected(self):
        connected, _ = await self.communicator(AnonymousUser()).connect()
        self.assertFalse(connected)

    async def test_non_participant_is_rejected(self):
        connected, _ = await self.communicator(self.eve_user).connect()
        self.assertFalse(connected)

    async def test_participants_exchange_messages(self):
        alice, bob = self.communicator(self.alice_user), self.communicator(self.bob_user)
        self.assertTrue((await alice.connect())[0])
        self.assertTrue((await bob.connect())[0])

        await alice.send_json_to({"message": "hello bob"})
        received = await bob.receive_json_from()
        self.assertEqual(received["message"], "hello bob")
        self.assertEqual(received["sender"], "alice")

        self.assertEqual(await database_sync_to_async(Message.objects.count)(), 1)
        await alice.disconnect()
        await bob.disconnect()

    async def test_invalid_payload_gets_an_error(self):
        alice = self.communicator(self.alice_user)
        await alice.connect()
        await alice.send_to(text_data="not json")
        self.assertIn("error", await alice.receive_json_from())
        await alice.disconnect()
