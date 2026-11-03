from django import forms

from .models import UserProfile
from .utils import validate_adult

MAX_HOBBIES = 20
MAX_HOBBY_LENGTH = 40


class ProfileForm(forms.ModelForm):
    hobbies = forms.CharField(
        required=False,
        max_length=800,
        label="Hobbies",
        help_text="Comma-separated, e.g. hiking, painting, yoga",
    )

    class Meta:
        model = UserProfile
        fields = [
            "user_birth_date", "gender", "gender_preference", "user_location",
            "user_bio", "occupation", "height_cm", "preference", "education",
            "religion", "religion_preference", "hair_color", "ethnicity",
            "relationship_history", "hobbies",
        ]
        labels = {
            "user_birth_date": "Date of birth",
            "gender": "I am",
            "gender_preference": "Interested in",
            "user_location": "Location",
            "user_bio": "About me",
            "height_cm": "Height (cm)",
            "preference": "Looking for",
            "religion": "Religion",
            "religion_preference": "Religion preference",
            "hair_color": "Hair colour",
            "relationship_history": "Relationship history",
        }
        widgets = {
            "user_birth_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "user_bio": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user_birth_date"].required = True
        self.fields["gender"].required = True
        if self.instance and self.instance.pk:
            self.initial["hobbies"] = ", ".join(self.instance.hobbies or [])

    def clean_user_birth_date(self):
        return validate_adult(self.cleaned_data.get("user_birth_date"))

    def clean_height_cm(self):
        height = self.cleaned_data.get("height_cm")
        if height is not None and not 120 <= height <= 250:
            raise forms.ValidationError("Enter a height between 120 and 250 cm.")
        return height

    def clean_hobbies(self):
        raw = self.cleaned_data.get("hobbies") or ""
        hobbies = []
        for item in raw.split(","):
            item = item.strip().lower()
            if not item or item in hobbies:
                continue
            if len(item) > MAX_HOBBY_LENGTH:
                raise forms.ValidationError(
                    f"Each hobby must be at most {MAX_HOBBY_LENGTH} characters."
                )
            hobbies.append(item)
        if len(hobbies) > MAX_HOBBIES:
            raise forms.ValidationError(f"Please list at most {MAX_HOBBIES} hobbies.")
        return hobbies
