from django.conf import settings

from . import embeddings_loader as loader


def compute_embeddings(profile):
    """Vectors for a profile, ready for QuerySet.update(). Empty if disabled."""
    if not getattr(settings, "ENABLE_EMBEDDINGS", True):
        return {}

    hobbies = [
        hobby.strip().lower()
        for hobby in (profile.hobbies or [])
        if isinstance(hobby, str) and hobby.strip()
    ]
    return {
        "hobbies_vec": loader.embed_hobbies(hobbies) if hobbies else None,
        "religion_vec": loader.category_vector("religion", profile.religion),
        "education_vec": loader.category_vector("education", profile.education),
    }