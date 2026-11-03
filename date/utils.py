import datetime

from django.core.exceptions import ValidationError

MIN_AGE = 18
MAX_AGE = 120


def calculate_age(birth_date, today=None):
    """Whole years since birth_date (None if unknown). Correct on birthdays."""
    if not birth_date:
        return None
    today = today or datetime.date.today()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def validate_adult(birth_date, today=None):
    """Raise ValidationError unless birth_date is a plausible 18+ date."""
    age = calculate_age(birth_date, today)
    if age is None:
        raise ValidationError("Date of birth is required.")
    if age < 0:
        raise ValidationError("Date of birth cannot be in the future.")
    if age < MIN_AGE:
        raise ValidationError(f"You must be at least {MIN_AGE} years old to use Stareye.")
    if age > MAX_AGE:
        raise ValidationError("Please enter a valid date of birth.")
    return birth_date
