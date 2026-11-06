from django.test import TestCase, override_settings
from django.urls import reverse

from . import services
from .forms import ProfileForm
from .testing import adult_birth_date, make_user


@override_settings(ENABLE_EMBEDDINGS=False)
class SetLocationTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_user("alice", gender="f", latitude=None, longitude=None)
        self.client.force_login(self.user)

    def post(self, **data):
        self.client.post(reverse("location"), data)
        self.profile.refresh_from_db()
        return self.profile

    def test_coordinates_are_snapped_before_saving(self):
        profile = self.post(latitude="40.71281", longitude="-74.00601")
        self.assertEqual((profile.latitude, profile.longitude), (40.71, -74.01))

    def test_bad_input_changes_nothing(self):
        for data in [{"latitude": "abc", "longitude": "1"}, {"latitude": "91", "longitude": "0"},
                     {"latitude": "nan", "longitude": "0"}, {"latitude": "40"}, {}]:
            with self.subTest(data=data):
                self.assertIsNone(self.post(**data).latitude)

    def test_clear_location(self):
        self.post(latitude="40", longitude="-74")
        self.assertEqual(self.client.post(reverse("clear-location")).status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual((self.profile.latitude, self.profile.longitude), (None, None))
        self.assertFalse(self.profile.is_complete())

    def test_login_required_and_clear_needs_post(self):
        self.assertEqual(self.client.get(reverse("clear-location")).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("location")).status_code, 302)


@override_settings(ENABLE_EMBEDDINGS=False)
class DistanceTests(TestCase):
    def setUp(self):
        # Roughly 7.8 km, 55.6 km and 222 km north of "me".
        self.me_user, self.me = make_user("me", gender="f", latitude=40.0, longitude=-74.0)
        self.bob_user, self.bob = make_user("bob", gender="m", latitude=40.07, longitude=-74.0)
        self.dave_user, self.dave = make_user("dave", gender="m", latitude=40.5, longitude=-74.0)
        self.far_user, self.far = make_user("far", gender="m", latitude=42.0, longitude=-74.0)
        self.client.force_login(self.me_user)

    def names(self):
        return [i["profile"].user.username for i in services.get_recommendations(self.me)]

    def test_pages_show_buckets_never_coordinates(self):
        feed = self.client.get(reverse("feed"))
        self.assertContains(feed, "Less than 10 km away")
        self.assertContains(feed, "Less than 75 km away")
        self.assertContains(feed, "More than 200 km away")
        profile = self.client.get(reverse("profile-detail", args=[self.bob_user.id]))
        self.assertContains(profile, "Less than 10 km away")
        for page in (feed, profile):
            for hidden in ("40.07", "40.5", "42.0"):
                self.assertNotContains(page, hidden)

    def test_users_can_hide_their_distance(self):
        self.bob.show_distance = False
        self.bob.save()
        feed = self.client.get(reverse("feed"))
        self.assertContains(feed, "bob")
        self.assertNotContains(feed, "Less than 10 km away")

    def test_equal_scores_are_ordered_nearest_first(self):
        self.assertEqual(self.names(), ["bob", "dave", "far"])

    def test_my_maximum_distance_filters_the_feed(self):
        self.me.max_distance_km = 25
        self.me.save()
        self.assertEqual(self.names(), ["bob"])

    def test_their_maximum_distance_applies_too(self):
        self.dave.max_distance_km = 25        # dave doesn't want anyone 55 km away
        self.dave.save()
        self.assertEqual(self.names(), ["bob", "far"])

    def test_missing_viewer_location_means_no_filtering_or_labels(self):
        self.me.latitude = self.me.longitude = None
        self.me.max_distance_km = 5
        self.me.save()
        items = services.get_recommendations(self.me)
        self.assertEqual({i["profile"].user.username for i in items}, {"bob", "dave", "far"})
        self.assertTrue(all(i["distance_label"] is None for i in items))

    def test_distance_preferences_are_editable_on_the_profile_form(self):
        data = {"user_birth_date": adult_birth_date().isoformat(), "gender": "f",
                "gender_preference": "everyone", "religion_preference": "neutral"}
        form = ProfileForm({**data, "max_distance_km": "50"}, instance=self.me)   # box unchecked
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.me.refresh_from_db()
        self.assertEqual(self.me.max_distance_km, 50)
        self.assertFalse(self.me.show_distance)
