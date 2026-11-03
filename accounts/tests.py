from django.test import TestCase

# Create your tests here.
import datetime

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from date.models import UserProfile


@override_settings(ENABLE_EMBEDDINGS=False)
class SignupTests(TestCase):
    def post_signup(self, **overrides):
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password1": "S3cure-pass-phrase!",
            "password2": "S3cure-pass-phrase!",
            "birth_date": "1990-01-01",
        }
        data.update(overrides)
        return self.client.post(reverse("signup"), data)

    def test_signup_creates_user_and_profile_with_birth_date(self):
        response = self.post_signup()
        self.assertRedirects(response, reverse("edit-profile"))
        profile = UserProfile.objects.get(user__username="newuser")
        self.assertEqual(profile.user_birth_date, datetime.date(1990, 1, 1))

    def test_minors_are_rejected(self):
        response = self.post_signup(birth_date=datetime.date.today().isoformat())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user("existing", "new@example.com", "pw-12345-xyz")
        response = self.post_signup()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_weak_password_is_rejected(self):
        response = self.post_signup(password1="password", password2="password")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())


@override_settings(ENABLE_EMBEDDINGS=False)
class LoginTests(TestCase):
    def test_login_redirects_to_feed(self):
        User.objects.create_user("alice", "a@example.com", "pw-12345-xyz")
        response = self.client.post(
            reverse("login"), {"username": "alice", "password": "pw-12345-xyz"}
        )
        self.assertRedirects(response, reverse("feed"), fetch_redirect_response=False)

    def test_logout_requires_post(self):
        user = User.objects.create_user("alice", "a@example.com", "pw-12345-xyz")
        self.client.force_login(user)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
