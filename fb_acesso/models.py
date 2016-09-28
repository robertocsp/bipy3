from __future__ import unicode_literals

from django.db import models


class Fb_acesso(models.Model):
    page_id = models.CharField(primary_key=True, max_length=128, blank=False, null=False)
    page_access_token = models.CharField(max_length=500, blank=False, null=False)
