import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from . import image_utils, services
from .models import ProfileImage

TMP_MEDIA = tempfile.mkdtemp(prefix="stareye-test-media-")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def make_image(fmt="JPEG", size=(800, 600), mode="RGB", color=(200, 30, 30), exif=None):
    buffer = BytesIO()
    image = Image.new(mode, size, color)
    kwargs = {"exif": exif} if exif else {}
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def upload(data, name="me.jpg", content_type="image/jpeg"):
    return SimpleUploadedFile(name, data, content_type=content_type)


class ProcessUploadTests(TestCase):
    def test_output_is_jpeg_and_resized(self):
        out = image_utils.process_upload(upload(make_image(size=(4000, 3000))))
        image = Image.open(BytesIO(out.read()))
        self.assertEqual(image.format, "JPEG")
        self.assertLessEqual(max(image.size), image_utils.MAX_DIMENSION)

    def test_png_and_webp_are_accepted(self):
        for fmt in ("PNG", "WEBP"):
            out = image_utils.process_upload(upload(make_image(fmt=fmt), name=f"x.{fmt.lower()}"))
            self.assertEqual(Image.open(BytesIO(out.read())).format, "JPEG")

    def test_transparent_png_goes_on_white(self):
        data = make_image(fmt="PNG", mode="RGBA", color=(0, 0, 0, 0))
        out = image_utils.process_upload(upload(data, name="t.png"))
        pixel = Image.open(BytesIO(out.read())).getpixel((10, 10))
        self.assertTrue(all(channel > 240 for channel in pixel))

    def test_exif_gps_is_stripped(self):
        exif = Image.Exif()
        exif[0x010F] = "SecretCameraMaker"
        gps = exif.get_ifd(0x8825)
        gps[2] = (40.0, 44.0, 54.0)
        gps[1] = "N"
        out = image_utils.process_upload(upload(make_image(exif=exif.tobytes())))
        data = out.read()
        self.assertNotIn(b"SecretCameraMaker", data)
        result = Image.open(BytesIO(data))
        self.assertEqual(len(result.getexif()), 0)
        self.assertNotIn("exif", result.info)

    def test_exif_orientation_is_applied(self):
        exif = Image.Exif()
        exif[0x0112] = 6  # rotate 90 degrees clockwise to display
        out = image_utils.process_upload(upload(make_image(size=(800, 400), exif=exif.tobytes())))
        self.assertEqual(Image.open(BytesIO(out.read())).size, (400, 800))

    def test_rejects_non_image(self):
        with self.assertRaises(ValidationError):
            image_utils.process_upload(upload(b"<script>alert(1)</script>", name="x.jpg"))

    def test_rejects_unsupported_format(self):
        with self.assertRaises(ValidationError):
            image_utils.process_upload(upload(make_image(fmt="GIF"), name="x.gif"))

    def test_rejects_oversize_file(self):
        big = SimpleUploadedFile("big.jpg", b"0" * (image_utils.MAX_UPLOAD_BYTES + 1))
        with self.assertRaises(ValidationError):
            image_utils.process_upload(big)

    def test_rejects_tiny_image(self):
        with self.assertRaises(ValidationError):
            image_utils.process_upload(upload(make_image(size=(50, 50))))

    def test_rejects_truncated_image(self):
        with self.assertRaises(ValidationError):
            image_utils.process_upload(upload(make_image()[:200]))


@override_settings(MEDIA_ROOT=TMP_MEDIA, STORAGES=STORAGES)
class PhotoViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user("maya", password="pw-12345-pw", first_name="Maya")
        self.profile = services.get_profile(self.user)
        self.client.login(username="maya", password="pw-12345-pw")

    def post_photos(self, *datas):
        files = [upload(d, name=f"p{i}.jpg") for i, d in enumerate(datas)]
        return self.client.post(reverse("upload-photos"), {"photos": files})

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("upload-photos"), {})
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
        self.assertEqual(ProfileImage.objects.count(), 0)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse("upload-photos")).status_code, 405)

    def test_upload_stores_sanitised_jpeg_with_random_name(self):
        response = self.post_photos(make_image(size=(3000, 2000)))
        self.assertRedirects(response, reverse("edit-profile"), fetch_redirect_response=False)
        photo = self.profile.images.get()
        self.assertTrue(photo.image.name.startswith("images/"))
        self.assertTrue(photo.image.name.endswith(".jpg"))
        self.assertNotIn("p0", photo.image.name)
        with photo.image.open("rb") as handle:
            self.assertLessEqual(max(Image.open(handle).size), image_utils.MAX_DIMENSION)

    def test_multiple_files_keep_upload_order(self):
        self.post_photos(make_image(color=(1, 2, 3)), make_image(color=(4, 5, 6)))
        positions = list(self.profile.images.values_list("position", flat=True))
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(positions), 2)

    def test_limit_is_enforced(self):
        self.post_photos(*[make_image() for _ in range(image_utils.MAX_PHOTOS + 2)])
        self.assertEqual(self.profile.images.count(), image_utils.MAX_PHOTOS)
        response = self.post_photos(make_image())
        self.assertEqual(self.profile.images.count(), image_utils.MAX_PHOTOS)
        self.assertEqual(response.status_code, 302)

    def test_invalid_file_is_rejected_and_nothing_saved(self):
        response = self.client.post(
            reverse("upload-photos"), {"photos": [upload(b"not an image", name="evil.jpg")]}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ProfileImage.objects.count(), 0)

    def test_no_files(self):
        response = self.client.post(reverse("upload-photos"), {})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ProfileImage.objects.count(), 0)

    def test_delete_removes_row_and_file(self):
        self.post_photos(make_image())
        photo = self.profile.images.get()
        storage, name = photo.image.storage, photo.image.name
        self.assertTrue(storage.exists(name))
        self.client.post(reverse("delete-photo", args=[photo.id]))
        self.assertEqual(ProfileImage.objects.count(), 0)
        self.assertFalse(storage.exists(name))

    def test_cannot_delete_or_promote_someone_elses_photo(self):
        other = User.objects.create_user("sam", password="pw-12345-pw")
        theirs = ProfileImage.objects.create(
            user=services.get_profile(other), image=image_utils.process_upload(upload(make_image()))
        )
        self.assertEqual(self.client.post(reverse("delete-photo", args=[theirs.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("set-main-photo", args=[theirs.id])).status_code, 404)
        self.assertTrue(ProfileImage.objects.filter(pk=theirs.pk).exists())

    def test_delete_requires_post(self):
        self.post_photos(make_image())
        photo = self.profile.images.get()
        self.assertEqual(self.client.get(reverse("delete-photo", args=[photo.id])).status_code, 405)

    def test_make_main_moves_photo_first(self):
        self.post_photos(make_image(), make_image(), make_image())
        first, _, third = list(self.profile.images.all())
        self.client.post(reverse("set-main-photo", args=[third.id]))
        ordered = list(self.profile.images.all())
        self.assertEqual(ordered[0].pk, third.pk)
        self.assertEqual({p.pk for p in ordered}, {first.pk, third.pk, _.pk})

    def test_account_deletion_removes_files(self):
        self.post_photos(make_image())
        photo = self.profile.images.get()
        storage, name = photo.image.storage, photo.image.name
        self.user.delete()
        self.assertFalse(storage.exists(name))

    def test_partial_renders_counts_and_controls(self):
        self.post_photos(make_image(), make_image())
        html = render_to_string(
            "partials/photo_manager.html",
            {"profile": self.profile, "max_photos": image_utils.MAX_PHOTOS},
            request=None,
        )
        self.assertIn("2 / 6", html)
        self.assertIn("Main photo", html)
        self.assertEqual(html.count("Make main"), 1)
        self.assertIn(reverse("upload-photos"), html)
        self.assertIn("multipart/form-data", html)
