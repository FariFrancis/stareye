import datetime
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from date.models import UserProfile
from recommend.management.commands.backfill_embeddings import needs_backfill

FAKE_VEC = [0.1, 0.2, 0.3]


def fake_category_vector(kind, label):
    return FAKE_VEC if label else None


@override_settings(ENABLE_EMBEDDINGS=True)
class BackfillTests(TestCase):
    def make_profile(self, name, **fields):
        # Created with embeddings off so the save signal doesn't fill vectors itself.
        with override_settings(ENABLE_EMBEDDINGS=False):
            user = User.objects.create_user(name, password="x")
            profile = UserProfile.objects.get(user=user)
            for key, value in fields.items():
                setattr(profile, key, value)
            profile.user_birth_date = datetime.date(1995, 1, 1)
            profile.save()
        return UserProfile.objects.get(pk=profile.pk)

    def run_cmd(self, *args):
        out, err = StringIO(), StringIO()
        call_command("backfill_embeddings", *args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def patches(self):
        return (
            mock.patch("recommend.embeddings_loader.embed_hobbies", return_value=FAKE_VEC),
            mock.patch("recommend.embeddings_loader.category_vector", side_effect=fake_category_vector),
        )

    def test_fills_missing_vectors_only_for_profiles_that_need_them(self):
        needy = self.make_profile("needy", hobbies=["hiking"], religion="atheist", education="masters")
        empty = self.make_profile("empty")
        done = self.make_profile("done", hobbies=["art"], hobbies_vec=[9.0], religion="", education="")
        h, c = self.patches()
        with h as embed, c:
            out, _ = self.run_cmd()
        needy.refresh_from_db(); empty.refresh_from_db(); done.refresh_from_db()
        self.assertEqual(needy.hobbies_vec, FAKE_VEC)
        self.assertEqual(needy.religion_vec, FAKE_VEC)
        self.assertEqual(needy.education_vec, FAKE_VEC)
        self.assertIsNone(empty.hobbies_vec)
        self.assertEqual(done.hobbies_vec, [9.0])          # already had one: untouched
        self.assertEqual(embed.call_count, 1)               # only `needy` was computed
        self.assertIn("updated 1, skipped 2, failed 0", out)

    def test_second_run_finds_nothing_to_do(self):
        self.make_profile("p", hobbies=["hiking"], religion="atheist", education="masters")
        h, c = self.patches()
        with h, c:
            self.run_cmd()
            out, _ = self.run_cmd()
        self.assertIn("updated 0", out)

    def test_does_not_change_updated_at(self):
        profile = self.make_profile("p", hobbies=["hiking"])
        before = profile.updated_at
        h, c = self.patches()
        with h, c:
            self.run_cmd()
        profile.refresh_from_db()
        self.assertEqual(profile.updated_at, before)
        self.assertEqual(profile.hobbies_vec, FAKE_VEC)

    def test_dry_run_writes_nothing(self):
        profile = self.make_profile("p", hobbies=["hiking"])
        h, c = self.patches()
        with h as embed, c:
            out, _ = self.run_cmd("--dry-run")
        profile.refresh_from_db()
        self.assertIsNone(profile.hobbies_vec)
        self.assertEqual(embed.call_count, 0)
        self.assertIn("would update 1", out)

    def test_all_recomputes_existing_vectors(self):
        profile = self.make_profile("p", hobbies=["hiking"], hobbies_vec=[9.0])
        h, c = self.patches()
        with h, c:
            self.run_cmd("--all")
        profile.refresh_from_db()
        self.assertEqual(profile.hobbies_vec, FAKE_VEC)

    def test_limit(self):
        for name in ("a", "b", "c"):
            self.make_profile(name, hobbies=["x"])
        h, c = self.patches()
        with h, c:
            out, _ = self.run_cmd("--limit", "2")
        self.assertIn("updated 2", out)
        self.assertEqual(UserProfile.objects.exclude(hobbies_vec__isnull=True).count(), 2)

    @override_settings(ENABLE_EMBEDDINGS=False)
    def test_exits_quietly_when_embeddings_are_off(self):
        profile = self.make_profile("p", hobbies=["hiking"])
        out, _ = self.run_cmd()
        profile.refresh_from_db()
        self.assertIn("off", out)
        self.assertIsNone(profile.hobbies_vec)

    def test_aborts_with_clear_error_when_model_cannot_load(self):
        self.make_profile("p", hobbies=["hiking"])
        with mock.patch("recommend.embeddings_loader.embed_hobbies", side_effect=OSError("no model")):
            with self.assertRaisesMessage(CommandError, "Could not compute embeddings"):
                self.run_cmd()

    def test_one_bad_profile_does_not_stop_the_rest(self):
        self.make_profile("a", hobbies=["one"])
        self.make_profile("b", hobbies=["boom"])
        self.make_profile("c", hobbies=["three"])

        def embed(hobbies):
            if hobbies == ["boom"]:
                raise ValueError("bad row")
            return FAKE_VEC

        with mock.patch("recommend.embeddings_loader.embed_hobbies", side_effect=embed), \
                mock.patch("recommend.embeddings_loader.category_vector", side_effect=fake_category_vector):
            out, err = self.run_cmd()
        self.assertIn("updated 2", out)
        self.assertIn("failed 1", out)
        self.assertIn("bad row", err)

    def test_needs_backfill_rules(self):
        p = UserProfile(hobbies=[], religion="", education="")
        self.assertFalse(needs_backfill(p))
        self.assertTrue(needs_backfill(UserProfile(hobbies=["a"])))
        self.assertFalse(needs_backfill(UserProfile(hobbies=["a"], hobbies_vec=[1.0])))
        self.assertTrue(needs_backfill(UserProfile(religion="atheist")))
        self.assertTrue(needs_backfill(UserProfile(education="masters", hobbies_vec=[1.0])))
        self.assertFalse(needs_backfill(UserProfile(hobbies=["   "])))


class DownloadCommandTests(TestCase):
    def run_cmd(self):
        out = StringIO()
        call_command("download_embedding_model", stdout=out)
        return out.getvalue()

    @override_settings(ENABLE_EMBEDDINGS=False)
    def test_skips_when_embeddings_are_off(self):
        with mock.patch("recommend.embeddings_loader.get_model") as get_model:
            out = self.run_cmd()
        get_model.assert_not_called()
        self.assertIn("skipping", out)

    @override_settings(ENABLE_EMBEDDINGS=True)
    def test_loads_model_when_on(self):
        model = mock.Mock()
        model.encode.return_value = [0.0] * 384
        with mock.patch("recommend.embeddings_loader.get_model", return_value=model):
            out = self.run_cmd()
        model.encode.assert_called_once()
        self.assertIn("384 dimensions", out)

    @override_settings(ENABLE_EMBEDDINGS=True)
    def test_fails_the_build_with_a_clear_message_if_model_cannot_load(self):
        with mock.patch("recommend.embeddings_loader.get_model", side_effect=OSError("offline")):
            with self.assertRaisesMessage(CommandError, "Could not load"):
                self.run_cmd()


class LoaderCacheTests(TestCase):
    def test_model_is_loaded_into_the_project_cache_folder(self):
        from recommend import embeddings_loader as loader

        fake_module = mock.Mock()
        loader.get_model.cache_clear()
        with mock.patch.dict("sys.modules", {"sentence_transformers": fake_module}):
            loader.get_model()
        loader.get_model.cache_clear()
        fake_module.SentenceTransformer.assert_called_once_with(
            loader.MODEL_NAME, cache_folder=str(loader.MODEL_CACHE_DIR)
        )
        self.assertEqual(loader.MODEL_CACHE_DIR.name, ".model_cache")
