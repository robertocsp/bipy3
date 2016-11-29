"""marviin URL Configuration

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

from marviin.rest import views
from marviin.views import *
from dashboard.views import *
from pedido.views import *
from upload_cardapio.views import *
from download_cardapio.views import *
from relacionamento.views import *

import logging

logger = logging.getLogger('django')

urlpatterns = [
    url(r'^$', login_geral, name='login_geral'),
    url(r'^logout/$', logout_geral, name='logout'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^cadastro/$', cadastro, name='cadastro'),
    url(r'^dashboard/$', dashboard, name='Dashboard'),
    url(r'^historico/$', historico_pedidos, name='historico'),
    url(r'^home/$', home, name='Home'),
    url(r'^marviin/api/rest/login[/]?$', views.LoginView.as_view(), name='login_view'),
    url(r'^marviin/api/rest/cliente[/]?$', views.ClienteView.as_view(), name='adicionar_cliente_view'),
    url(r'^marviin/api/rest/cliente/(?P<fbpk>[0-9]+)/touch[/]?$', views.ClienteTouchView.as_view(),
        name='touch_cliente_view'),
    url(r'^marviin/api/rest/pedido[/]?$', views.EnviarPedidoView.as_view(), name='enviar_pedido_view'),
    url(r'^marviin/api/rest/pedido/(?P<uid>[0-9]+)/chat[/]?$', views.PedidoChatView.as_view(),
        name='enviar_pedido_view'),
    url(r'^marviin/api/rest/status[/]?$', views.StatusPedidoView.as_view(), name='status_pedido_view'),
    url(r'^marviin/api/rest/mensagem[/]?$', views.EnviarMensagemView.as_view(), name='enviar_mensagem_view'),
    url(r'^marviin/api/rest/mensagem_bot[/]?$', views.EnviarMensagemBotView.as_view(), name='enviar_mensagem_bot_view'),
    url(r'^marviin/api/rest/troca_mesa[/]?$', views.TrocarMesaView.as_view(), name='trocar_mesa_view'),
    url(r'^marviin/api/rest/pede_cardapio[/]?$', views.PedirCardapioView.as_view(), name='pedir_cardapio_view'),
    url(r'^marviin/api/rest/pede_garcom[/]?$', views.ChamarGarcomView.as_view(), name='chamar_garcom_view'),
    url(r'^marviin/api/rest/pede_conta[/]?$', views.PedirContaView.as_view(), name='pedir_conta_view'),
    url(r'^marviin/api/rest/notificacao_lida[/]?$', views.NotificacaoLidaView.as_view(), name='notificacao_lida_view'),
    url(r'^marviin/api/rest/acesso_bot[/]?$', views.AcessoBotView.as_view(), name='acesso_bot_view'),
    url(r'^marviin/api/rest/page_access_token[/]?$', views.PageAccessTokenView.as_view(),
        name='page_access_token_view'),
    url(r'^marviin/api/rest/cardapio[/]?$', views.CardapioView.as_view(), name='cardapio_view'),
    url(r'^marviin/api/rest/pesquisa_estabelecimento[/]?$', views.FormularioInteresseView.as_view(),
        name='pesquisa_estabelecimento_view'),
    url(r'^marviin/api/rest/indicacao_usuario[/]?$', views.FormularioIndicacaoView.as_view(),
        name='indicacao_usuario_view'),
    url(r'^pedidos/$', pedidos, name='pedidos'),
    url(r'^pedidos-delivery/$', pedidos_delivery, name='pedidos_delivery'),
    url(r'^upload/$', upload, name='upload'),
    url(r'^cadastrar-cardapio/$', cadastraCardapio, name='cadastra-cardapio'),
    url(r'^upload-cardapio/$', FileFieldView.as_view(), name='upload-cardapio'),
    url(r'^download-cardapio/$', download_cardapio, name='download-cardapio'),
    url(r'^termos-e-condicoes-de-uso/$', termos, name='termos'),
    url(r'^relacionamento/$', relacionamento, name='relacionamento')]
