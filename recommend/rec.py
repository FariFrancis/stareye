# Compatibility filters and batch similarity scoring with torch.
# The feed scores one user against *many* candidates, so the hot path is
# vectorised: each signal (hobbies / religion / education embeddings, height) is
# turned into one tensor over all candidates and scored with a single matrix
# operation, instead of building a tensor per pair.



import torch

SIMILARITY_WEIGHTS = {
    "hobbies": 0.40,
    "height": 0.15,
    "education": 0.20,
    "religion": 0.25,
}

# Keys must match date.models.gender_preference_options.
GENDER_PREF = {
    "everyone": ["m", "f", "o"],
    "male_only": ["m"],
    "female_only": ["f"],
    "non_binary_only": ["o"],
    "male_female": ["m", "f"],
}

# Height difference (cm) at which the height score reaches zero.
HEIGHT_RANGE_CM = 50

VECTOR_FIELDS = (
    ("hobbies", "hobbies_vec"),
    ("religion", "religion_vec"),
    ("education", "education_vec"),
)


# Dealbreaker filters

def _accepts(preference, gender):
    if not preference or preference == "everyone":
        return True
    return gender in GENDER_PREF.get(preference, ())


def gender_compatible(a, b):
    return _accepts(a.gender_preference, b.gender) and _accepts(b.gender_preference, a.gender)


def religion_compatible(a, b):
    for person, other in ((a, b), (b, a)):
        if person.religion_preference == "dealbreaker" and person.religion != other.religion:
            return False
    return True


religion_filter = religion_compatible 


def is_compatible(a, b):
    return gender_compatible(a, b) and religion_compatible(a, b)


# Scoring system

def _cosine_scores(query_vec, candidate_vecs, clamp=True):
    """Cosine similarity of one vector against many.

    Returns (scores, mask), both of length len(candidate_vecs). mask[i] is
    False when candidate i (or the query) has no usable vector: missing,
    wrong length, or all zeros. Those scores are 0 and must be ignored.
    """
    n = len(candidate_vecs)
    scores = torch.zeros(n)
    mask = torch.zeros(n, dtype=torch.bool)
    if not query_vec or n == 0:
        return scores, mask

    dim = len(query_vec)
    rows, positions = [], []
    for position, vec in enumerate(candidate_vecs):
        if vec and len(vec) == dim:
            rows.append(vec)
            positions.append(position)
    if not rows:
        return scores, mask

    query = torch.tensor(query_vec, dtype=torch.float32)
    query_norm = query.norm()
    if query_norm == 0:
        return scores, mask

    matrix = torch.tensor(rows, dtype=torch.float32)       # (m, dim)
    norms = matrix.norm(dim=1)                              # (m,)
    usable = norms > 0
    similarity = (matrix @ query) / (norms.clamp_min(1e-12) * query_norm)
    if clamp:
        similarity = similarity.clamp(0.0, 1.0)

    index = torch.tensor(positions, dtype=torch.long)
    scores[index] = similarity * usable
    mask[index] = usable
    return scores, mask


def _height_scores(my_height, heights):
    n = len(heights)
    if not my_height or n == 0:
        return torch.zeros(n), torch.zeros(n, dtype=torch.bool)
    values = torch.tensor([h or 0 for h in heights], dtype=torch.float32)
    mask = torch.tensor([bool(h) for h in heights], dtype=torch.bool)
    scores = (1 - (values - my_height).abs() / HEIGHT_RANGE_CM).clamp(0.0, 1.0)
    return scores * mask, mask


def compare(v1, v2):
    """Cosine similarity of two vectors, or None if either is unusable."""
    scores, mask = _cosine_scores(v1, [v2], clamp=False)
    return float(scores[0]) if bool(mask[0]) else None


@torch.inference_mode()
def score_candidates(me, candidates):
    """Similarity in [0, 1] of `me` to every candidate, as a tensor.

    Does NOT apply the hard filters; use rank_candidates() or filter with
    is_compatible() first.
    """
    n = len(candidates)
    if n == 0:
        return torch.zeros(0)

    parts = {
        key: _cosine_scores(getattr(me, attr, None), [getattr(c, attr, None) for c in candidates])
        for key, attr in VECTOR_FIELDS
    }
    parts["height"] = _height_scores(me.height_cm, [c.height_cm for c in candidates])

    weighted = torch.zeros(n)
    total_weight = torch.zeros(n)
    for key, (scores, mask) in parts.items():
        weight = SIMILARITY_WEIGHTS[key]
        weighted += scores * mask * weight
        total_weight += mask.float() * weight

    return torch.where(
        total_weight > 0,
        weighted / total_weight.clamp_min(1e-12),
        torch.zeros(n),
    )


@torch.inference_mode()
def rank_candidates(me, candidates, limit=50):
    """Compatible candidates, best first, as [(candidate, score), ...].

    Ties keep the input order (stable sort), so callers control tie-breaking
    by ordering the candidates they pass in.
    """
    compatible = [c for c in candidates if is_compatible(me, c)]
    if not compatible:
        return []
    scores = score_candidates(me, compatible)
    ordered_scores, order = torch.sort(scores, descending=True, stable=True)
    keep = min(limit, len(compatible))
    return [
        (compatible[i], s)
        for i, s in zip(order[:keep].tolist(), ordered_scores[:keep].tolist())
    ]




def compute_similarity(a, b):
    return float(score_candidates(a, [b])[0])


def match_score(a, b):
    """0.0 for incompatible pairs, otherwise a similarity in [0, 1]."""
    if not is_compatible(a, b):
        return 0.0
    return compute_similarity(a, b)