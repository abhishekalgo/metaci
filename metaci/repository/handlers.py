from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver
from metaci.repository.models import Repository


@receiver(pre_save, sender=Repository)
def get_github_id(sender, **kwargs):
    repo = kwargs["instance"]
    if not repo.github_id:
        repo.github_id = repo.github_api.id
