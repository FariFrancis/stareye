from django.db import models
from sentence_transformers import SentenceTransformer
from date.models import UserProfile
import torch
import zipfile
import pandas as pd
# Create your models here.
model = SentenceTransformer('all-MiniLM-L6-v2')
# Load ZIP
with zipfile.ZipFile('hobbies.zip') as z:
    with z.open('hobbies.csv') as f:
        df = pd.read_csv(f, on_bad_lines='skip')

edu_df = pd.read_csv("education.csv")
relig_df = pd.read_csv("religion.csv")

def embed(path, column):
    df = pd.read_csv(path)
    return {row[column]: model.encode(row[column]) for r, row in df.iterrows()}

relig_emb = embed("religion.csv", "religion")
edu_emb = embed("education.csv", "education")

df = df.drop_duplicates(subset='HOBBIES').reset_index(drop=True)
df['HOBBIES'] = df['HOBBIES'].astype(str).str.lower()


def compare(v1, v2):
    v1 = torch.tensor(v1)
    v2 = torch.tensor(v2)
    return torch.nn.functional.cosine_similarity(v1, v2, dim=0).item()

class MockUser:
    def __init__(self, username, gender, gender_preference, religion, religion_preference, education, height_cm, hobbies):
        self.username = username
        self.gender = gender
        self.gender_preference = gender_preference
        self.religion = religion
        self.religion_preference = religion_preference
        self.education = education
        self.height_cm = height_cm
        self.hobbies = hobbies
        self.hobbies_vec = model.encode(" ".join(hobbies))
        
SIMILARITY_WEIGHTS = {
    "hobbies": 0.40,
    "height": 0.15,
    "education": 0.20,
    "religion": 0.25,
}


GENDER_PREF = {
    "everyone": ["male", "female", "non_binary"],
    "male_only": ["male"],
    "female_only": ["female"],
    "non_binary_only": ["non_binary"],
    "male_female": ["male", "female"],
}


def gender_compatible(a, b):
    return (b.gender in GENDER_PREF[a.gender_preference] and
            a.gender in GENDER_PREF[b.gender_preference])

def religion_filter(a, b):
    return not (
        (a.religion_preference == "dealbreaker" and a.religion != b.religion) or
        (b.religion_preference == "dealbreaker" and b.religion != a.religion)
    )


def compute_similarity(a, b):
    scores = {
        "hobbies": compare(a.hobbies_vec, b.hobbies_vec),
        "religion": compare(relig_emb[a.religion], relig_emb[b.religion]),
        "education": compare(edu_emb[a.education], edu_emb[b.education]),
        "height": 1 - abs(a.height_cm - b.height_cm) / 200
    }

    return sum(scores[key] * SIMILARITY_WEIGHTS[key] for key in scores)


def match_score(a, b):
    if not gender_compatible(a, b):
        return 0
    if not religion_filter(a, b):
        return 0
    return compute_similarity(a, b)

user1 = MockUser(
    username="alice",
    gender="female",
    gender_preference="male_only",
    religion="christian",
    religion_preference="neutral",
    education="bachelor",
    height_cm=165,
    hobbies=["hiking", "painting", "yoga"]
)

user2 = MockUser(
    username="bob",
    gender="male",
    gender_preference="female_only",
    religion="muslim",
    religion_preference="neutral",
    education="master",
    height_cm=180,
    hobbies=["rock climbing", "camping", "hiking"]
)

user3 = MockUser(
    username="charlie",
    gender="male",
    gender_preference="everyone",
    religion="atheist",
    religion_preference="neutral",
    education="high_school",
    height_cm=170,
    hobbies=["video games", "coding", "anime"]
)

user4 = MockUser(
    username="diana",
    gender="female",
    gender_preference="female_only",
    religion="christian",
    religion_preference="neutral",
    education="phd",
    height_cm=160,
    hobbies=["reading", "research", "writing"]
)

user5 = MockUser(
    username="John",
    gender="male",
    gender_preference="everyone",
    religion="christian",
    religion_preference="dealbreaker",
    education="masters",
    height_cm=180,
    hobbies=["reading", "painting", "writing"]
)

users = [user2, user3, user4, user5]

print("\nMatches for Alice:\n")

for u in users:
    score = match_score(user1, u)
    print(f"{user1.username} vs {u.username}: {score:.3f}")