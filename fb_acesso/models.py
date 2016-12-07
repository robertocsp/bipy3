from __future__ import unicode_literals

from django.db import models, connection
from utils import BigAutoField


class Fb_acesso(models.Model):
    page_id = models.CharField(primary_key=True, max_length=128, blank=False, null=False)
    page_access_token = models.CharField(max_length=500, blank=False, null=False)
    app_scoped_user_id = models.CharField(max_length=128, blank=True, null=True)


class FbContasUsuario(models.Model):
    id = BigAutoField(primary_key=True, editable=False)
    app_scoped_user_id = models.CharField(max_length=128, blank=False, null=False)
    page_id = models.CharField(max_length=128, blank=False, null=False)
    page_name = models.CharField(max_length=100, blank=False, null=False)
    page_access_token = models.CharField(max_length=500, blank=False, null=False)


def remove_not_eligible_pages(app_scoped_user_id):
    with connection.cursor() as cursor:
        cursor.execute('DELETE c FROM fb_acesso_fbcontasusuario AS c INNER JOIN fb_acesso_fb_acesso AS a ON '
                       'a.page_id=c.page_id')
        cursor.execute("DELETE c FROM fb_acesso_fbcontasusuario AS c WHERE c.app_scoped_user_id != %s",
                       [app_scoped_user_id])


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
