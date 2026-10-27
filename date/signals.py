from django.db.models.signals import post_save
from django.dispatch import receiver
from date.models import UserProfile
from recommend.embedding_loader import model, relig_emb, edu_emb

@receiver(post_save, sender=UserProfile)
def generate_embeddings(sender, instance, **kwargs):
    from recommend.embedding_loader import model, relig_emb, edu_emb

    # Hobbies embedding
    if instance.hobbies:
        instance.hobbies_vec = model.encode(" ".join(instance.hobbies)).tolist()

    # Religion embedding
    if instance.religion:
        instance.religion_vec = relig_emb.get(instance.religion)

    # Education embedding
    if instance.education:
        instance.education_vec = edu_emb.get(instance.education)

    instance.save()
