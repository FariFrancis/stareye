from django.db import models
from django.contrib.auth.models import User
# Create your models here.

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

class UserProfile(models.Model):
    user = models.OneToOneField(User, primary_key = True, on_delete=models.CASCADE)
    user_Birth_Date = models.DateField(null=True, blank=True)
    user_Descrip = models.TextField(max_length=500, blank = True)
    user_Location = models.CharField(max_length=100, blank=True)

    matched = models.ManyToManyField(
        "self",
        related_name="matched_with",
        symmetrical=False,
        blank=True
    )


    gender = models.CharField(max_length=1, choices=Gender_Options, blank=True)


    preference = models.CharField(max_length=20, choices=Preferences, blank = True)
    creation_date = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class UserConnections(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    matched = models.ManyToManyField(
        "self",
        related_name="matched_with",
        symmetrical=False,
        blank=True
    )


    def __str__(self):
        return f"People {self.user.user.username} has matched with"