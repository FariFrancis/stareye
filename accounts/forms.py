from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from date.models import UserProfile
from date.utils import validate_adult


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    birth_date = forms.DateField(
        label="Date of birth",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_birth_date(self):
        return validate_adult(self.cleaned_data.get("birth_date"))

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            # The post_save signal has already created the profile.
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.user_birth_date = self.cleaned_data["birth_date"]
            profile.save()
        return user


class ChangeEmailForm(forms.Form):
    email = forms.EmailField()

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Email already in use.")
        return email
