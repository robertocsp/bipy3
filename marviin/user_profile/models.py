from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=30, blank=True, null=True)
    token_senha = models.CharField('token_senha', max_length=200, null=True, blank=True)


@receiver(pre_save, sender=User)
def create_not_active_user(sender, instance, **kwargs):
    try:
        User.objects.get(username=instance.username)
    except User.DoesNotExist:
        instance.is_active = False


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except ObjectDoesNotExist:
        Profile.objects.create(user=instance)
