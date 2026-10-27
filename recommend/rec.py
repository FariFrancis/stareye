import torch

SIMILARITY_WEIGHTS = {
    "hobbies": 0.40,
    "height": 0.15,
    "education": 0.20,
    "religion": 0.25,
}

GENDER_PREF = {
    "everyone": ["m", "f", "o"],
    "male_only": ["m"],
    "female_only": ["f"],
    "non_binary_only": ["o"],
    "male_female": ["m", "f"],
}

def compare(v1, v2):
    v1 = torch.tensor(v1)
    v2 = torch.tensor(v2)
    return torch.nn.functional.cosine_similarity(v1, v2, dim=0).item()

def gender_compatible(a, b):
    return (
        b.gender in GENDER_PREF[a.gender_preference] and
        a.gender in GENDER_PREF[b.gender_preference]
    )

def religion_filter(a, b):
    return not (
        (a.religion_preference == "dealbreaker" and a.religion != b.religion) or
        (b.religion_preference == "dealbreaker" and b.religion != a.religion)
    )

def compute_similarity(a, b):
    scores = {
        "hobbies": compare(a.hobbies_vec, b.hobbies_vec),
        "religion": compare(a.religion_vec, b.religion_vec),
        "education": compare(a.education_vec, b.education_vec),
        "height": 1 - abs(a.height_cm - b.height_cm) / 200,
    }

    return sum(scores[key] * SIMILARITY_WEIGHTS[key] for key in scores)

def match_score(a, b):
    if not gender_compatible(a, b):
        return 0
    if not religion_filter(a, b):
        return 0
    return compute_similarity(a, b)
