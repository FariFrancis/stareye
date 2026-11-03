import datetime

from django.contrib.auth.models import User

from .models import UserProfile


def adult_birth_date(years=30):
    today = datetime.date.today()
    return datetime.date(today.year - years, 1, 1)


def make_user(name, gender="m", gender_preference="everyone", **profile_fields):
    user = User.objects.create_user(name, f"{name}@example.com", "pw-12345-xyz")
    profile = UserProfile.objects.get(user=user)
    profile.user_birth_date = adult_birth_date()
    profile.gender = gender
    profile.gender_preference = gender_preference
    for field, value in profile_fields.items():
        setattr(profile, field, value)
    profile.save()
    return user, profile
