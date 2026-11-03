import os
import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from .utils import calculate_age

preferences = [
    ('casual', 'Casual'),
    ('serious', 'Serious'),
    ('marriage', 'Marriage'),
]

gender_options = [
    ('m', 'Male'),
    ('f', 'Female'),
    ('o', 'Other'),
]

# Keys must match recommend.rec.GENDER_PREF.
gender_preference_options = [
    ('everyone', 'Everyone'),
    ('male_only', 'Men only'),
    ('female_only', 'Women only'),
    ('non_binary_only', 'Non-binary only'),
    ('male_female', 'Men and women'),
]

religion_preference_options = [
    ('neutral', 'No preference'),
    ('dealbreaker', 'Must share my religion'),
]

hair_color_options = [
    ('black', 'Black'),
    ('blonde', 'Blonde'),
    ('brown', 'Brown'),
    ('red', 'Red'),
    ('grey', 'Grey'),
    ('bald', 'Bald'),
    ('blue', 'Blue'),
    ('pink', 'Pink'),
    ('green', 'Green'),
    ('purple', 'Purple'),
    ('other', 'Other'),
]

ethnicity_options = [
    ('white', 'White'),
    ('asian', 'Asian'),
    ('black', 'Black'),
    ('mixed', 'Mixed'),
    ('hispanic', 'Hispanic'),
    ('other_ethnicity', 'Other Ethnicity'),
]

religion_options = [
    ('christian', 'Christian'),
    ('muslim', 'Muslim'),
    ('hindu', 'Hindu'),
    ('jewish', 'Jewish'),
    ('buddhist', 'Buddhist'),
    ('atheist', 'Atheist'),
    ('agnostic', 'Agnostic'),
    ('spiritual', 'Spiritual'),
]

relationship_history_options = [
    ('never_married', 'Never Married'),
    ('divorced', 'Divorced'),
    ('widowed', 'Widowed'),
    ('separated', 'Separated'),
]

# Keys must match education.csv (used for the education embeddings).
education_options = [
    ('high_school', 'High School'),
    ('college', 'College'),
    ('bachelors', 'Bachelors Degree'),
    ('masters', 'Masters'),
    ('phd', 'PhD / Post Doctoral'),
]

match_status_options = [
    ("pending", "Pending"),
    ("accepted", "Accepted"),
    ("rejected", "Rejected"),
]


class UserProfile(models.Model):
    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE)

    user_birth_date = models.DateField(null=True, blank=True)
    user_bio = models.TextField(max_length=500, blank=True)
    user_location = models.CharField(max_length=100, blank=True)
    occupation = models.CharField(max_length=100, blank=True)

    religion = models.CharField(max_length=50, choices=religion_options, blank=True)
    religion_preference = models.CharField(
        max_length=20, choices=religion_preference_options, default='neutral'
    )

    height_cm = models.PositiveIntegerField(null=True, blank=True)

    preference = models.CharField(max_length=20, choices=preferences, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=gender_options, null=True, blank=True)
    gender_preference = models.CharField(
        max_length=20, choices=gender_preference_options, default='everyone'
    )

    hair_color = models.CharField(max_length=30, choices=hair_color_options, null=True, blank=True)
    ethnicity = models.CharField(max_length=20, choices=ethnicity_options, null=True, blank=True)
    relationship_history = models.CharField(
        max_length=30, choices=relationship_history_options, null=True, blank=True
    )
    education = models.CharField(max_length=30, choices=education_options, null=True, blank=True)

    hobbies = models.JSONField(default=list, blank=True)

    # Embeddings for the recommendation system (generated in date/signals.py).
    hobbies_vec = models.JSONField(null=True, blank=True)
    religion_vec = models.JSONField(null=True, blank=True)
    education_vec = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def age(self):
        return calculate_age(self.user_birth_date)

    def is_complete(self):
        """Minimum info needed to appear in (and use) the feed."""
        return bool(self.user_birth_date and self.gender)

    def __str__(self):
        return f"{self.user.username}'s Profile"


def image_filename(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return os.path.join('images', f"{uuid.uuid4()}{ext}")


class ProfileImage(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=image_filename, blank=True)

    def __str__(self):
        return f"Image for {self.user.user.username}"


class Match(models.Model):
    """A match request. `matcher` asks, `matchee` accepts or rejects."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

    matcher = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="matches_sent",
    )
    matchee = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="matches_received",
    )

    status = models.CharField(max_length=10, choices=match_status_options, default="pending")
    matched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["matcher", "matchee"],
                name="unique_match"
            )
        ]

    def clean(self):
        if self.matcher_id == self.matchee_id:
            raise ValidationError("Users cannot match themselves")

        if self._state.adding and Match.objects.filter(
            matcher=self.matchee, matchee=self.matcher
        ).exists():
            raise ValidationError("This match already exists in reverse.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matcher.user.username} -> {self.matchee.user.username} ({self.status})"


class Block(models.Model):
    blocker = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="blocks_made"
    )
    blocked = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="blocks_received"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="unique_block"
            )
        ]

    def clean(self):
        if self.blocker_id == self.blocked_id:
            raise ValidationError("Users cannot block themselves")

    def __str__(self):
        return f"{self.blocker.user.username} blocked {self.blocked.user.username}"
