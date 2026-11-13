import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import ProfileImage, UserProfile

logger = logging.getLogger(__name__)

EMBEDDING_SOURCE_FIELDS = {"hobbies", "religion", "education"}


@receiver(post_save, sender=User, dispatch_uid="date_create_profile")
def create_profile(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=UserProfile, dispatch_uid="date_generate_embeddings")
def generate_embeddings(sender, instance, created, raw=False, update_fields=None, **kwargs):
    if raw:
        return
    if update_fields and not EMBEDDING_SOURCE_FIELDS & set(update_fields):
        return

    try:
        from recommend.services import compute_embeddings

        vectors = compute_embeddings(instance)
    except Exception:
        logger.exception("Embedding generation failed for profile %s", instance.pk)
        return

    if not vectors or (created and not any(vectors.values())):
        return
    UserProfile.objects.filter(pk=instance.pk).update(**vectors)


@receiver(post_delete, sender=ProfileImage, dispatch_uid="date_delete_image_file")
def delete_image_file(sender, instance, **kwargs):
    if not instance.image:
        return
    try:
        instance.image.delete(save=False)
    except Exception:
        logger.exception("Could not delete stored file for photo %s", instance.pk)
