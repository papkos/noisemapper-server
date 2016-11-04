from django.db import models


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
