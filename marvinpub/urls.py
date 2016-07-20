"""marvinpub URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import TemplateView

from marvinpub.rest import views
from marvinpub.views import *
from dashboard.views import *

urlpatterns = [
    url(r'^$', login_geral, name='login_geral'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^dashboard/$', TemplateView.as_view(template_name='dashboard.html'), name="dashboard"),
    url(r'^marvin/api/rest/pedido[/]?$', views.EnviarPedidoView.as_view(), name='enviar_pedido_view'),
    url(r'^home/$', home, name='Home'),
    url(r'^upload/$', upload, name='upload'),
    url(r'^pedidos/$', pedidos, name='pedidos'),
    url(r'^historico/$', historico_pedidos, name='Home'),
    url(r'^cadastro/$', cadastro, name='Home')
]
