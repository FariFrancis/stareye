from django.test import TestCase

# Create your tests here.
import unittest
from types import SimpleNamespace

from recommend import rec


def person(**overrides):
    fields = dict(
        gender="m", gender_preference="everyone",
        religion="christian", religion_preference="neutral",
        height_cm=175, hobbies_vec=None, religion_vec=None, education_vec=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


class CosineTests(unittest.TestCase):
    def test_identical_vectors(self):
        self.assertAlmostEqual(rec.cosine_similarity([1, 2, 3], [1, 2, 3]), 1.0)

    def test_orthogonal_vectors(self):
        self.assertAlmostEqual(rec.cosine_similarity([1, 0], [0, 1]), 0.0)

    def test_unusable_vectors_return_none(self):
        self.assertIsNone(rec.cosine_similarity(None, [1, 2]))
        self.assertIsNone(rec.cosine_similarity([1, 2], [1]))
        self.assertIsNone(rec.cosine_similarity([0, 0], [1, 2]))


class CompatibilityTests(unittest.TestCase):
    def test_gender_preferences_must_be_mutual(self):
        alice = person(gender="f", gender_preference="male_only")
        bob = person(gender="m", gender_preference="female_only")
        carol = person(gender="f", gender_preference="female_only")
        self.assertTrue(rec.is_compatible(alice, bob))
        self.assertFalse(rec.is_compatible(alice, carol))   # alice wants men
        self.assertFalse(rec.is_compatible(bob, carol))     # carol wants women, bob is a man

    def test_unknown_gender_only_matches_open_preferences(self):
        unknown = person(gender=None)
        self.assertTrue(rec.is_compatible(person(), unknown))
        self.assertFalse(rec.is_compatible(person(gender_preference="female_only"), unknown))

    def test_religion_dealbreaker_applies_both_ways(self):
        strict = person(religion="christian", religion_preference="dealbreaker")
        self.assertTrue(rec.is_compatible(strict, person(religion="christian")))
        self.assertFalse(rec.is_compatible(strict, person(religion="muslim")))
        self.assertFalse(rec.is_compatible(person(religion="muslim"), strict))


class ScoreTests(unittest.TestCase):
    def test_incompatible_pair_scores_zero(self):
        a = person(gender_preference="female_only")
        self.assertEqual(rec.match_score(a, person(gender="m")), 0.0)

    def test_missing_signals_do_not_crash(self):
        self.assertEqual(rec.match_score(person(height_cm=None), person(height_cm=None)), 0.0)

    def test_height_only_score(self):
        score = rec.match_score(person(height_cm=170), person(height_cm=170))
        self.assertAlmostEqual(score, 1.0)
        far = rec.match_score(person(height_cm=150), person(height_cm=200))
        self.assertAlmostEqual(far, 0.0)

    def test_similar_hobbies_beat_different_hobbies(self):
        me = person(hobbies_vec=[1.0, 0.0, 0.0])
        close = person(hobbies_vec=[0.9, 0.1, 0.0])
        far = person(hobbies_vec=[0.0, 1.0, 0.0])
        self.assertGreater(rec.match_score(me, close), rec.match_score(me, far))

    def test_weights_are_renormalised(self):
        # Only hobbies available -> score equals the hobby similarity itself.
        me = person(height_cm=None, hobbies_vec=[1.0, 0.0])
        other = person(height_cm=None, hobbies_vec=[1.0, 0.0])
        self.assertAlmostEqual(rec.match_score(me, other), 1.0)


if __name__ == "__main__":
    unittest.main()
