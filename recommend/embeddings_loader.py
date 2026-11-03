import csv
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_NAME = "all-MiniLM-L6-v2"

CATEGORY_FILES = {
    "religion": BASE_DIR / "religion.csv",
    "education": BASE_DIR / "education.csv",
}


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def _read_labels(path, column):
    with open(path, newline="", encoding="utf-8") as handle:
        return [row[column].strip() for row in csv.DictReader(handle) if row.get(column)]


@lru_cache(maxsize=None)
def _category_table(kind):
    model = get_model()
    return {
        label: model.encode(label.replace("_", " ")).tolist()
        for label in _read_labels(CATEGORY_FILES[kind], kind)
    }


def embed_hobbies(hobbies):
    return get_model().encode(" ".join(hobbies)).tolist()


def category_vector(kind, label):
    # Embedding for a known religion/education label, else None.
    if not label:
        return None
    return _category_table(kind).get(label)
