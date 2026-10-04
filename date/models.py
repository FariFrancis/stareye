import datetime
import math
import uuid
import os
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from django.dispatch import receiver

Preferences: list[tuple[str, str]] = [
    ('Casual', 'casual'),
    ('Serious', 'serious'),
    ('Marriage', 'marriage'),
]

Gender_Options: list[tuple[str, str]] = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
]
Hair_Color: list[tuple[str, str]] = [
    ('BLACK', 'Black'),
    ('BLONDE', 'Blonde'),
    ('BROWN', 'Brown'),
    ('RED', 'Red'),
    ('GREY', 'Grey'),
    ('BALD', 'Bald'),
    ('BLUE', 'Blue'),
    ('PINK', 'Pink'),
    ('GREEN', 'Green'),
    ('PURPLE', 'Purple'),
    ('OTHER', 'Other'),
]
Ethnicity: list[tuple[str, str]] = [
    ('WHITE', 'White'),
    ('ASIAN', 'Asian'),
    ('BLACK', 'Black'),
    ('MIXED', 'Mixed'),
    ('HISPANIC', 'Hispanic'),
    ('OTHER ETHNICITY', 'Other Ethnicity')
]
Relationship_History: list[tuple[str, str]] = [
    ('NEVER MARRIED', 'Never Married'),
    ('DIVORCED', 'Divorced'),
    ('WIDOWED', 'Widowed'),
    ('SEPARATED', 'Separated')
]
Education: list[tuple[str, str]] = [
    ('HIGH SCHOOL', 'High School'),
    ('COLLEGE', 'College'),
    ('BACHELORS DEGREE', 'Bachelors Degree'),
    ('MASTERS', 'Masters'),
    ('PHD / POST DOCTORAL', 'PhD / Post Doctoral'),
]
STATUS: list[tuple[str, str]] = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        # ("unmatched", "Unmatched"),
        # ("blocked", "Blocked")
    ]

class UserProfile(models.Model):
    user = models.OneToOneField(User, primary_key = True, on_delete=models.CASCADE)
    user_Birth_Date = models.DateField(null=True, blank=True)
    user_Bio = models.TextField(max_length=500, blank = True)
    user_Location = models.CharField(max_length=100, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    preference = models.CharField(max_length=20, choices=Preferences, null=True, blank = True)
    gender = models.CharField(max_length=1, choices=Gender_Options, null=True, blank=True)
    hair = models.CharField(max_length=30, choices=Hair_Color, null=True, blank=True)
    ethnic = models.CharField(max_length=20, choices=Ethnicity, null=True, blank=True)
    rel_History = models.CharField(max_length=30, choices=Relationship_History, null=True, blank=True)
    education = models.CharField(max_length=30, choices=Education, null=True, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def age(self):
        if not self.user_Birth_Date:
            return None
        return int((datetime.date.today() - self.user_Birth_Date).days / 365.25 )
    def __str__(self):
        return f"{self.user.username}'s Profile"

def image_filename(instance, filename):
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    return os.path.join('images/', filename)

class ProfileImage(models.Model):

    # Optional and not needed for demo purposes
    # APPROVAL = (
    #     ('TO BE APPROVED', 'To be approved'),
    #     ('APPROVED', 'Approved'),
    #     ('NOT APPROVED', 'Not approved')
    # )
    
    user = models.ForeignKey(UserProfile, default=None, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=image_filename, blank=True)
    # is_verified = models.CharField(choices=APPROVAL, default="TO BE APPROVED", blank=False, max_length=14)


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

   
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
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
        return f"People {self.matcher.user.username} has matched with {self.matchee.user.username}"

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
