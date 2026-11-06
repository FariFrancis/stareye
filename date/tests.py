from django.test import TestCase

# Create your tests here.
import json

from django.test import TestCase, override_settings
from django.urls import reverse

from . import services
from .forms import ProfileForm
from .models import Block, Match
from .testing import adult_birth_date, make_user


@override_settings(ENABLE_EMBEDDINGS=False)
class MatchFlowTests(TestCase):
    def setUp(self):
        self.alice_user, self.alice = make_user("alice", gender="f")
        self.bob_user, self.bob = make_user("bob", gender="m")

    def test_request_then_accept(self):
        match, mutual = services.request_match(self.alice, self.bob)
        self.assertFalse(mutual)
        self.assertEqual(match.status, Match.PENDING)

        accepted = services.respond_to_match(self.bob, match.id, accept=True)
        self.assertEqual(accepted.status, Match.ACCEPTED)

    def test_mutual_request_accepts_existing_one(self):
        services.request_match(self.alice, self.bob)
        match, mutual = services.request_match(self.bob, self.alice)
        self.assertTrue(mutual)
        self.assertEqual(match.status, Match.ACCEPTED)
        self.assertEqual(Match.objects.count(), 1)

    def test_duplicate_request_is_rejected(self):
        services.request_match(self.alice, self.bob)
        with self.assertRaises(services.MatchError):
            services.request_match(self.alice, self.bob)

    def test_cannot_match_self(self):
        with self.assertRaises(services.MatchError):
            services.request_match(self.alice, self.alice)

    def test_only_the_recipient_can_respond(self):
        match, _ = services.request_match(self.alice, self.bob)
        with self.assertRaises(services.MatchError) as ctx:
            services.respond_to_match(self.alice, match.id, accept=True)
        self.assertEqual(ctx.exception.status, 404)

    def test_blocked_users_cannot_match(self):
        services.block_user(self.bob, self.alice)
        with self.assertRaises(services.MatchError):
            services.request_match(self.alice, self.bob)

    def test_create_match_view_redirects_for_forms_and_returns_json_for_api(self):
        self.client.force_login(self.alice_user)
        url = reverse("create-match", args=[self.bob_user.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.bob_user)
        response = self.client.post(
            reverse("create-match", args=[self.alice_user.id]),
            HTTP_ACCEPT="application/json",
        )
        # alice already asked bob, so bob's request completes the match
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["status"], "accepted")

    def test_match_views_require_post_and_login(self):
        url = reverse("create-match", args=[self.bob_user.id])
        self.assertEqual(self.client.post(url).status_code, 302)        # -> login
        self.client.force_login(self.alice_user)
        self.assertEqual(self.client.get(url).status_code, 405)


@override_settings(ENABLE_EMBEDDINGS=False)
class FeedTests(TestCase):
    def setUp(self):
        self.me_user, self.me = make_user("me", gender="f", gender_preference="male_only")
        self.bob_user, self.bob = make_user("bob", gender="m")
        self.carol_user, self.carol = make_user("carol", gender="f")
        self.dave_user, self.dave = make_user("dave", gender="m")
        self.erin_user, self.erin = make_user("erin", gender="m")

    def names(self):
        return {item["profile"].user.username for item in services.get_recommendations(self.me)}

    def test_filters_by_gender_preference_and_excludes_self(self):
        self.assertEqual(self.names(), {"bob", "dave", "erin"})

    def test_excludes_matched_and_blocked_users(self):
        services.request_match(self.me, self.bob)
        services.block_user(self.me, self.dave)
        self.assertEqual(self.names(), {"erin"})

    def test_excludes_users_who_blocked_me(self):
        services.block_user(self.erin, self.me)
        self.assertNotIn("erin", self.names())

    def test_excludes_profiles_without_birth_date(self):
        self.bob.user_birth_date = None
        self.bob.save()
        self.assertNotIn("bob", self.names())

    def test_feed_view_renders(self):
        self.client.force_login(self.me_user)
        response = self.client.get(reverse("feed"))
        self.assertContains(response, "bob")

    def test_incomplete_profile_is_prompted_to_finish(self):
        self.me.user_birth_date = None
        self.me.save()
        self.client.force_login(self.me_user)
        response = self.client.get(reverse("feed"))
        self.assertContains(response, "date of birth")


@override_settings(ENABLE_EMBEDDINGS=False)
class ProfileTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_user("alice", gender="f")

    def valid_data(self, **overrides):
        data = {
            "user_birth_date": adult_birth_date(28).isoformat(),
            "gender": "f",
            "gender_preference": "everyone",
            "religion_preference": "neutral",
            "height_cm": "170",
            "hobbies": "Hiking, painting, hiking",
        }
        data.update(overrides)
        return data

    def test_form_saves_hobbies_as_clean_list(self):
        form = ProfileForm(self.valid_data(), instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.hobbies, ["hiking", "painting"])
        self.assertEqual(self.profile.height_cm, 170)

    def test_form_rejects_minors_and_bad_heights(self):
        too_young = adult_birth_date(10).isoformat()
        self.assertFalse(ProfileForm(self.valid_data(user_birth_date=too_young),
                                     instance=self.profile).is_valid())
        self.assertFalse(ProfileForm(self.valid_data(height_cm="40"),
                                     instance=self.profile).is_valid())

    def test_edit_view_saves_and_redirects(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("edit-profile"), self.valid_data(user_bio="Hello"))
        self.assertRedirects(response, reverse("profile-detail", args=[self.user.id]))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.user_bio, "Hello")

    def test_profile_hidden_from_users_who_blocked_viewer(self):
        other_user, other = make_user("bob")
        Block.objects.create(blocker=other, blocked=self.profile)
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile-detail", args=[other_user.id]))
        self.assertEqual(response.status_code, 404)
