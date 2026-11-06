import io
import os
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from . import services
from .models import ProfileImage
from .testing import make_user


def png(size=(100, 80)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


class PhotoTests(TestCase):
    def setUp(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        overrides = override_settings(MEDIA_ROOT=media, ENABLE_EMBEDDINGS=False)
        overrides.enable()
        self.addCleanup(overrides.disable)
        self.user, self.profile = make_user("alice", gender="f", photo=False)
        self.client.force_login(self.user)

    def upload(self, data, name="pic.png"):
        return self.client.post(reverse("photos"), {"image": SimpleUploadedFile(name, data)})

    def test_upload_is_stored_as_a_resized_jpeg(self):
        self.assertRedirects(self.upload(png((3000, 2000))), reverse("photos"))
        with Image.open(self.profile.images.get().image.path) as stored:
            self.assertEqual(stored.format, "JPEG")
            self.assertEqual(max(stored.size), 1600)

    def test_exif_metadata_is_stripped(self):
        exif = Image.Exif()
        exif[0x010F] = "SecretCam"
        buffer = io.BytesIO()
        Image.new("RGB", (60, 40)).save(buffer, format="JPEG", exif=exif)
        self.upload(buffer.getvalue(), "pic.jpg")
        with Image.open(self.profile.images.get().image.path) as stored:
            self.assertEqual(dict(stored.getexif()), {})

    def test_non_images_are_rejected(self):
        self.assertEqual(self.upload(b"not an image", "evil.jpg").status_code, 200)
        self.assertEqual(self.profile.images.count(), 0)

    def test_photo_limit(self):
        with patch("date.views.MAX_PHOTOS", 1):
            self.upload(png())
            self.upload(png())
        self.assertEqual(self.profile.images.count(), 1)

    def test_delete_removes_row_and_file_but_only_for_the_owner(self):
        self.upload(png())
        photo = self.profile.images.get()
        path = photo.image.path
        other_user, other = make_user("bob", photo=False)
        theirs = ProfileImage.objects.create(user=other, image="images/bob.jpg")

        self.assertEqual(self.client.post(reverse("photo-delete", args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("photo-delete", args=[photo.pk])).status_code, 405)
        self.client.post(reverse("photo-delete", args=[photo.pk]))
        self.assertFalse(ProfileImage.objects.filter(pk=photo.pk).exists())
        self.assertFalse(os.path.exists(path))

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.upload(png()).status_code, 302)
        self.assertEqual(ProfileImage.objects.count(), 0)


@override_settings(ENABLE_EMBEDDINGS=False)
class FeedRuleTests(TestCase):
    """A profile needs a photo and a location to use the feed or appear in it."""

    def test_only_complete_profiles_are_shown(self):
        _, me = make_user("me", gender="f")
        make_user("bob", gender="m")
        make_user("nophoto", gender="m", photo=False)
        make_user("nowhere", gender="m", latitude=None, longitude=None)
        names = {i["profile"].user.username for i in services.get_recommendations(me)}
        self.assertEqual(names, {"bob"})

    def test_viewer_is_told_what_is_missing(self):
        me_user, _ = make_user("me", gender="f", photo=False, latitude=None, longitude=None)
        self.client.force_login(me_user)
        response = self.client.get(reverse("feed"))
        self.assertContains(response, "at least one photo")
        self.assertContains(response, "your location")
