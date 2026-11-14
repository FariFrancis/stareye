"""Download and load the embedding model once, during the build.

Without this, the first profile save on a freshly deployed server has to download
the model (around 90 MB) inside a web request. Put this in the build command:

    python manage.py download_embedding_model

It does nothing when ENABLE_EMBEDDINGS is off, so the same build command works
either way.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Download the embedding model into the project's model cache and check that it loads."

    def handle(self, *args, **options):
        if not getattr(settings, "ENABLE_EMBEDDINGS", True):
            self.stdout.write("ENABLE_EMBEDDINGS is off; skipping model download.")
            return

        from recommend import embeddings_loader as loader

        try:
            vector = loader.get_model().encode("warm up")
        except Exception as exc:
            raise CommandError(f"Could not load {loader.MODEL_NAME} ({exc.__class__.__name__}: {exc})") from exc
        self.stdout.write(
            f"Model {loader.MODEL_NAME} ready ({len(vector)} dimensions) in {loader.MODEL_CACHE_DIR}"
        )
