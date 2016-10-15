from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save


class SafeDeleteMixin(models.Model):

    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, really_delete=False):
        if really_delete:
            super(SafeDeleteMixin, self).delete(using=using, keep_parents=keep_parents)
        else:
            self.is_deleted = True
            self.save()


class NoiseMapperBase(SafeDeleteMixin, models.Model):
    class Meta:
        abstract = True


class Profile(NoiseMapperBase, models.Model):

    user = models.OneToOneField(User, related_name='profile_noisemapper')

    device_type = models.CharField(max_length=200, null=True, blank=True)


def _create_profile_for_user(sender, instance, created, **kwargs):
    if created:
        profile = Profile()
        profile.user = instance
        profile.save()


post_save.connect(_create_profile_for_user, sender=settings.AUTH_USER_MODEL)
