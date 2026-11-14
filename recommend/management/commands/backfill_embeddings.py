"""Fill in recommendation vectors for profiles that don't have them yet.

Profiles only get vectors when they are saved while ENABLE_EMBEDDINGS is on, so
anyone created (or edited) while it was off has none. Run this once after turning
embeddings on:

    python manage.py backfill_embeddings             # only profiles missing vectors
    python manage.py backfill_embeddings --dry-run   # show what it would do
    python manage.py backfill_embeddings --all       # recompute everyone

It is safe to run repeatedly (a run with nothing missing just scans and exits),
and it never changes `updated_at`, so the feed order isn't disturbed.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from date.models import UserProfile
from recommend.services import compute_embeddings


def needs_backfill(profile):
    """True if the profile has source data whose vector is missing."""
    hobbies = [h for h in (profile.hobbies or []) if isinstance(h, str) and h.strip()]
    return bool(
        (hobbies and not profile.hobbies_vec)
        or (profile.religion and not profile.religion_vec)
        or (profile.education and not profile.education_vec)
    )


class Command(BaseCommand):
    help = "Compute recommendation embeddings for profiles that are missing them."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Recompute every profile, not just those missing vectors.")
        parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing anything.")
        parser.add_argument("--limit", type=int, default=0, help="Stop after this many profiles (0 = no limit).")

    def handle(self, *args, **options):
        if not getattr(settings, "ENABLE_EMBEDDINGS", True):
            # Exit normally so this can sit in a build command while embeddings are off.
            self.stdout.write("ENABLE_EMBEDDINGS is off; nothing to do.")
            return

        updated = skipped = failed = 0
        for profile in UserProfile.objects.order_by("pk").iterator(chunk_size=100):
            if not (options["all"] or needs_backfill(profile)):
                skipped += 1
                continue
            if options["limit"] and updated >= options["limit"]:
                break
            if options["dry_run"]:
                updated += 1
                self.stdout.write(f"would update profile {profile.pk}")
                continue

            try:
                vectors = compute_embeddings(profile)
            except Exception as exc:
                if updated == 0 and failed == 0:
                    # First profile failed: the model itself is probably unavailable.
                    raise CommandError(f"Could not compute embeddings ({exc.__class__.__name__}: {exc})") from exc
                failed += 1
                self.stderr.write(f"profile {profile.pk}: {exc.__class__.__name__}: {exc}")
                continue

            if vectors:
                # update() skips signals and leaves updated_at alone.
                UserProfile.objects.filter(pk=profile.pk).update(**vectors)
            updated += 1

        verb = "would update" if options["dry_run"] else "updated"
        self.stdout.write(f"Done: {verb} {updated}, skipped {skipped}, failed {failed}.")
