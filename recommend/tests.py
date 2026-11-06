import random
import unittest
from types import SimpleNamespace

try:
    from recommend import rec
except ImportError:  # torch is not installed
    rec = None

needs_torch = unittest.skipIf(rec is None, "torch is not installed")


def person(**overrides):
    fields = dict(
        gender="m", gender_preference="everyone",
        religion="christian", religion_preference="neutral",
        height_cm=175, hobbies_vec=None, religion_vec=None, education_vec=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


# --- Pure-Python oracle used to cross-check the torch implementation --------

def oracle_cosine(v1, v2):
    if not v1 or not v2 or len(v1) != len(v2):
        return None
    n1 = sum(x * x for x in v1) ** 0.5
    n2 = sum(x * x for x in v2) ** 0.5
    if n1 == 0 or n2 == 0:
        return None
    return max(0.0, min(1.0, sum(x * y for x, y in zip(v1, v2)) / (n1 * n2)))


def oracle_score(a, b):
    scores = {}
    for key, attr in (("hobbies", "hobbies_vec"), ("religion", "religion_vec"),
                      ("education", "education_vec")):
        sim = oracle_cosine(getattr(a, attr), getattr(b, attr))
        if sim is not None:
            scores[key] = sim
    if a.height_cm and b.height_cm:
        scores["height"] = max(0.0, 1 - abs(a.height_cm - b.height_cm) / rec.HEIGHT_RANGE_CM)
    total = sum(rec.SIMILARITY_WEIGHTS[k] for k in scores)
    if not total:
        return 0.0
    return sum(scores[k] * rec.SIMILARITY_WEIGHTS[k] for k in scores) / total


@needs_torch
class CompareTests(unittest.TestCase):
    def test_identical_vectors(self):
        self.assertAlmostEqual(rec.compare([1, 2, 3], [1, 2, 3]), 1.0, places=5)

    def test_orthogonal_vectors(self):
        self.assertAlmostEqual(rec.compare([1, 0], [0, 1]), 0.0, places=5)

    def test_unusable_vectors_return_none(self):
        self.assertIsNone(rec.compare(None, [1, 2]))
        self.assertIsNone(rec.compare([1, 2], [1]))
        self.assertIsNone(rec.compare([0, 0], [1, 2]))


@needs_torch
class CompatibilityTests(unittest.TestCase):
    def test_gender_preferences_must_be_mutual(self):
        alice = person(gender="f", gender_preference="male_only")
        bob = person(gender="m", gender_preference="female_only")
        carol = person(gender="f", gender_preference="female_only")
        self.assertTrue(rec.is_compatible(alice, bob))
        self.assertFalse(rec.is_compatible(alice, carol))
        self.assertFalse(rec.is_compatible(bob, carol))

    def test_unknown_gender_only_matches_open_preferences(self):
        unknown = person(gender=None)
        self.assertTrue(rec.is_compatible(person(), unknown))
        self.assertFalse(rec.is_compatible(person(gender_preference="female_only"), unknown))

    def test_unknown_preference_value_matches_nobody_instead_of_crashing(self):
        self.assertFalse(rec.is_compatible(person(gender_preference="bogus"), person()))

    def test_religion_dealbreaker_applies_both_ways(self):
        strict = person(religion="christian", religion_preference="dealbreaker")
        self.assertTrue(rec.is_compatible(strict, person(religion="christian")))
        self.assertFalse(rec.is_compatible(strict, person(religion="muslim")))
        self.assertFalse(rec.is_compatible(person(religion="muslim"), strict))


@needs_torch
class ScoreTests(unittest.TestCase):
    def test_incompatible_pair_scores_zero(self):
        self.assertEqual(rec.match_score(person(gender_preference="female_only"), person()), 0.0)

    def test_missing_signals_do_not_crash(self):
        self.assertEqual(rec.match_score(person(height_cm=None), person(height_cm=None)), 0.0)

    def test_height_only_score(self):
        self.assertAlmostEqual(rec.match_score(person(height_cm=170), person(height_cm=170)), 1.0, places=5)
        self.assertAlmostEqual(rec.match_score(person(height_cm=150), person(height_cm=200)), 0.0, places=5)

    def test_similar_hobbies_beat_different_hobbies(self):
        me = person(hobbies_vec=[1.0, 0.0, 0.0])
        close = person(hobbies_vec=[0.9, 0.1, 0.0])
        far = person(hobbies_vec=[0.0, 1.0, 0.0])
        self.assertGreater(rec.match_score(me, close), rec.match_score(me, far))

    def test_weights_are_renormalised(self):
        me = person(height_cm=None, hobbies_vec=[1.0, 0.0])
        other = person(height_cm=None, hobbies_vec=[1.0, 0.0])
        self.assertAlmostEqual(rec.match_score(me, other), 1.0, places=5)

    def test_malformed_vectors_are_treated_as_missing(self):
        me = person(height_cm=None, hobbies_vec=[1.0, 0.0])
        wrong_length = person(height_cm=None, hobbies_vec=[1.0, 0.0, 0.0])
        zero = person(height_cm=None, hobbies_vec=[0.0, 0.0])
        self.assertEqual(rec.match_score(me, wrong_length), 0.0)
        self.assertEqual(rec.match_score(me, zero), 0.0)


@needs_torch
class BatchTests(unittest.TestCase):
    def random_person(self, rng, dim=8):
        def vec():
            roll = rng.random()
            if roll < 0.2:
                return None
            if roll < 0.25:
                return [0.0] * dim
            if roll < 0.3:
                return [rng.random() for _ in range(dim + 1)]   # wrong length
            return [rng.uniform(-1, 1) for _ in range(dim)]
        return person(
            height_cm=rng.choice([None, rng.randint(150, 200)]),
            hobbies_vec=vec(), religion_vec=vec(), education_vec=vec(),
        )

    def test_batch_matches_pure_python_oracle(self):
        rng = random.Random(1234)
        me = self.random_person(rng)
        me.height_cm, me.hobbies_vec = 172, [rng.uniform(-1, 1) for _ in range(8)]
        candidates = [self.random_person(rng) for _ in range(300)]

        batch = rec.score_candidates(me, candidates).tolist()
        self.assertEqual(len(batch), 300)
        for candidate, got in zip(candidates, batch):
            self.assertAlmostEqual(got, oracle_score(me, candidate), places=4)

    def test_empty_candidate_list(self):
        self.assertEqual(len(rec.score_candidates(person(), [])), 0)
        self.assertEqual(rec.rank_candidates(person(), []), [])

    def test_rank_orders_filters_and_limits(self):
        me = person(height_cm=170, gender_preference="female_only", gender="m")
        near = person(gender="f", height_cm=170)
        mid = person(gender="f", height_cm=185)
        far = person(gender="f", height_cm=210)
        wrong_gender = person(gender="m", height_cm=170)

        ranked = rec.rank_candidates(me, [far, wrong_gender, mid, near])
        self.assertEqual([c for c, _ in ranked], [near, mid, far])
        self.assertEqual(len(rec.rank_candidates(me, [far, mid, near], limit=2)), 2)
        scores = [s for _, s in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_ties_keep_input_order(self):
        me = person(height_cm=170)
        first, second, third = (person(height_cm=170) for _ in range(3))
        ranked = rec.rank_candidates(me, [first, second, third])
        self.assertEqual([c for c, _ in ranked], [first, second, third])


if __name__ == "__main__":
    unittest.main()