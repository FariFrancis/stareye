import datetime
import math
import uuid
import os
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from django.dispatch import receiver

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
    religion_preference = models.CharField(max_length=20, default='neutral')

    height_cm = models.PositiveIntegerField(null=True, blank=True)

    preference = models.CharField(max_length=20, choices=preferences, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=gender_options, null=True, blank=True)
    gender_preference = models.CharField(max_length=20, default='everyone')

    hair_color = models.CharField(max_length=30, choices=hair_color_options, null=True, blank=True)
    ethnicity = models.CharField(max_length=20, choices=ethnicity_options, null=True, blank=True)
    relationship_history = models.CharField(max_length=30, choices=relationship_history_options, null=True, blank=True)
    education = models.CharField(max_length=30, choices=education_options, null=True, blank=True)

    hobbies = models.JSONField(default=list, blank=True)

    # Embeddings for recommendation system
    hobbies_vec = models.JSONField(null=True, blank=True)
    religion_vec = models.JSONField(null=True, blank=True)
    education_vec = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def age(self):
        if not self.user_birth_date:
            return None
        return int((datetime.date.today() - self.user_birth_date).days / 365.25)

    def __str__(self):
        return f"{self.user.username}'s Profile"


def image_filename(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('images/', filename)


class ProfileImage(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=image_filename, blank=True)

    def __str__(self):
        return f"Image for {self.user.user.username}"


class Match(models.Model):
    matcher = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="matches_received"
    )
    matchee = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="matches_sent"
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
        if self.matcher == self.matchee:
            raise ValidationError("Users cannot match themselves")

        if Match.objects.filter(matcher=self.matchee, matchee=self.matcher).exists():
            raise ValidationError("This match already exists in reverse.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matcher.user.username} matched with {self.matchee.user.username}"

# class Block(models.Model):
#     blocker = models.ForeignKey(
#         UserProfile,
#         on_delete=models.CASCADE,
#         related_name="blocks_made"
#     )
#     blocked = models.ForeignKey(
#         UserProfile,
#         on_delete=models.CASCADE,
#         related_name="blocks_received"
#     )
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         constraints = [
#             models.UniqueConstraint(
#                 fields=["blocker", "blocked"],
#                 name="unique_block"
#             )
#         ]

#     def __str__(self):
#         return f"{self.blocker.user.username} blocked {self.blocked.user.username}"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
