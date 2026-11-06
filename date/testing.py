"""Helpers shared by the test suites (not a test module itself)."""
import datetime

from django.contrib.auth.models import User

from .models import ProfileImage, UserProfile


def adult_birth_date(years=30):
    today = datetime.date.today()
    return datetime.date(today.year - years, 1, 1)


def make_user(name, gender="m", gender_preference="everyone", photo=True,
              latitude=40.0, longitude=-74.0, **profile_fields):
    """A complete profile (birth date, gender, a photo and a location) unless told otherwise.

    Pass photo=False, or latitude=None / longitude=None, to build an incomplete one.
    The photo row points at a made-up file name; no file is written.
    """
    user = User.objects.create_user(name, f"{name}@example.com", "pw-12345-xyz")
    profile = UserProfile.objects.get(user=user)
    profile.user_birth_date = adult_birth_date()
    profile.gender = gender
    profile.gender_preference = gender_preference
    profile.latitude = latitude
    profile.longitude = longitude
    for field, value in profile_fields.items():
        setattr(profile, field, value)
    profile.save()
    if photo:
        ProfileImage.objects.create(user=profile, image=f"images/{name}.jpg")
    return user, profile
