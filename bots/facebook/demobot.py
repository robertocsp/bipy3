# -*- coding: utf-8 -*-
"""
This bot listens to port 5002 for incoming connections from Facebook.
"""
import os
import logging
import requests
import json
import unicodedata
import datetime
import base64
import time
import memcache

from string import Template
from flask import Flask, request, send_from_directory, Response
from logging.handlers import RotatingFileHandler
from logging import Formatter
from celery import Celery, chain
from celery.exceptions import SoftTimeLimitExceeded
from contextlib import contextmanager
from itertools import product
from string import ascii_lowercase

try:
    from urllib.parse import parse_qs, urlencode
except ImportError:
    from urlparse import parse_qs
    from urllib import urlencode


logging_handler = RotatingFileHandler(filename='/var/log/bot/demoindoorbot.log', maxBytes=5*1024*1024, backupCount=2)
logging_handler.setFormatter(Formatter(logging.BASIC_FORMAT, None))
app_log = logging.getLogger('root')
app_log.setLevel(logging.DEBUG)
app_log.addHandler(logging_handler)


def make_celery(app):
    celery = Celery('demobot', broker='amqp://rabbitbot:rabbitbot@localhost/rabbitbotvhost', backend='rpc://')
    celery.conf.update(app.config)
    taskbase = celery.Task

    class ContextTask(taskbase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return taskbase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery

flask_app = Flask(__name__)
celery_app = make_celery(flask_app)
cache = memcache.Client(['127.0.0.1:11211'])

FACEBOOK_GRAPH_URL = "https://graph.facebook.com/v2.7"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
with open(os.path.join(os.path.join(BASE_DIR, 'marviin_conf'), 'keys.txt')) as keys_file:
    for line in keys_file:
        key_value_pair = line.strip().split('=')
        if key_value_pair[0] == 'super_user_user':
            SUPER_USER_USER = key_value_pair[1]
        if key_value_pair[0] == 'super_user_password':
            SUPER_USER_PASSWORD = key_value_pair[1]
        if key_value_pair[0] == 'api-secret':
            CHAVE_BOT_API_INTERNA = key_value_pair[1]
        if key_value_pair[0] == 'webhook-secret':
            CHAVE_BOT_WEBHOOK = key_value_pair[1]

saudacao = ['ola', 'oi', 'bom dia', 'boa tarde', 'boa noite']
agradecimentos = ['obrigado', 'obrigada', 'valeu', 'vlw', 'flw']
EXPIRACAO_CACHE_CONVERSA = 60 * 60 * 2  # 2 horas
EXPIRACAO_CACHE_LOJA = 60 * 60 * 24 * 30  # 30 dias
EXPIRACAO_CACHE_LOCK = 15  # tempo de vida do lock é de 15 segundos, no caso de um erro.
POSTBACK_MAP = {
    'menu_novo_pedido': u'Novo pedido',
    'pedir_cardapio': u'Pedir cardápio',
    'chamar_garcom': u'Chamar garçom',
    'menu_trocar_mesa': u'Definir mesa',
    'pedir_conta': u'Pedir a conta',
    'finalizar_pedido': u'Enviar pedido',
    'pedir_mais': u'+ itens ao pedido',
    'menu_rever_pedido': u'Atualizar pedido',
    'menu_get_started': u'Menu principal',
    'editar_item_': u'Editar item',
    'remover_item_': u'Remover item',
    'vermais_offset_': u'Ver mais itens',
}
ROBOT_ICON = u'\U0001f4bb'
# ULTIMO PASSO = 31


class GraphAPIError(Exception):
    def __init__(self, result):
        self.result = result
        self.code = None
        try:
            self.type = result["error_code"]
        except:
            self.type = ""

        # OAuth 2.0 Draft 10
        try:
            self.message = result["error_description"]
        except:
            # OAuth 2.0 Draft 00
            try:
                self.message = result["error"]["message"]
                self.code = result["error"].get("code")
                if not self.type:
                    self.type = result["error"].get("type", "")
            except:
                # REST server style
                try:
                    self.message = result["error_msg"]
                except:
                    self.message = result

        Exception.__init__(self, self.message)


@celery_app.task(bind=True, soft_time_limit=7)
def get_object(self, fb_id, loja_id, **args):
    return fb_request('/' + fb_id, loja_id, args=args)


def post(loja_id, post_args=None, json=None, files=None, headers=None):
    time_start = datetime.datetime.now().replace(microsecond=0)
    result = fb_request('/me/messages', loja_id, post_args=post_args, json=json, files=files, headers=headers)
    delta_t = datetime.datetime.now().replace(microsecond=0) - time_start
    app_log.debug('=========================>>>>> facebook call delta t ' + repr(delta_t.total_seconds()) + 's')
    app_log.debug('=========================>>>>> facebook call result ' + repr(result))
    return result


def fb_request(path, loja_id, args=None, post_args=None, json=None, files=None, method=None, headers=None):
    args = args or {}

    if post_args is not None or json is not None:
        method = "POST"

    access_token = cache.get(loja_id + 'pac')
    if access_token is None:
        access_token = get_page_access_token(loja_id)
        app_log.debug('=========================>>>>> access token call result ' + repr(access_token))
        if access_token:
            cache.set(loja_id + 'pac', access_token, time=EXPIRACAO_CACHE_LOJA)
        else:
            # TODO pensar no que fazer em caso de erro.
            return

    args["access_token"] = access_token

    try:
        response = requests.request(method or "GET",
                                    FACEBOOK_GRAPH_URL + path,
                                    params=args,
                                    data=post_args,
                                    json=json,
                                    files=files,
                                    headers=headers)
    except requests.RequestException as e:
        response = json.loads(e.read())
        app_log.error('!!!ERROR!!! ' + repr(response))
        raise GraphAPIError(response)

    headers = response.headers
    if 'json' in headers['content-type']:
        result = response.json()
    elif 'image/' in headers['content-type']:
        mimetype = headers['content-type']
        result = {"data": response.content,
                  "mime-type": mimetype,
                  "url": response.url}
    elif "access_token" in parse_qs(response.text):
        query_str = parse_qs(response.text)
        if "access_token" in query_str:
            result = {"access_token": query_str["access_token"][0]}
            if "expires" in query_str:
                result["expires"] = query_str["expires"][0]
        else:
            raise GraphAPIError(response.json())
    else:
        raise GraphAPIError('Maintype was not text, image, or querystring')

    if result and isinstance(result, dict) and result.get("error"):
        raise GraphAPIError(result)
    return result


def get_page_access_token(page_id):
    payload = {'chave_bot_api_interna': CHAVE_BOT_API_INTERNA, 'page_id': page_id}
    url = 'http://localhost:8888/marviin/api/rest/page_access_token'
    headers = {'Authorization': 'Basic ' + base64.b64encode(SUPER_USER_USER + ':' + SUPER_USER_PASSWORD)}
    response = requests.get(url, params=payload, headers=headers)
    res_json = response.json()
    app_log.debug('=========================>>>>> access token call result ' + repr(res_json))
    if 'success' in res_json and res_json['success'] == True:
        return res_json['access_token']
    return None


def send_image_message(sender_id, loja_id, image_path, content_type):
    payload = {
        'recipient': json.dumps(
            {
                'id': sender_id
            }
        ),
        'message': json.dumps(
            {
                'attachment': {
                    'type': 'image',
                    'payload': {}
                }
            }
        )
    }
    multipart_data = {'filedata': (image_path, open(image_path, 'rb'), content_type)}
    return post(loja_id, post_args=payload, files=multipart_data)


@celery_app.task(bind=True, soft_time_limit=7)
def send_image_url_message(self, sender_id, loja_id, url, icon=ROBOT_ICON):
    payload = {
        'recipient': {
            'id': sender_id
        },
        'message': {
            'attachment': {
                'type': 'image',
                'payload': {
                    'url': url
                }
            }
        }
    }
    return post(loja_id, json=payload)


def send_button_message(sender_id, loja_id, text, buttons):
    payload = {
        'recipient': {
            'id': sender_id
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': [
                        {
                            'title': ROBOT_ICON + ': ' + text,
                            'buttons': buttons
                        }
                    ]
                }
            }
        }
    }
    return post(loja_id, json=payload)


@celery_app.task(bind=True, soft_time_limit=7)
def send_text_message(self, sender_id, loja_id, text, icon=ROBOT_ICON):
    if icon:
        payload_text = icon + ': ' + text
    else:
        payload_text = text
    payload = {
        'recipient': {
            'id': sender_id
        },
        'message': {
            'text': payload_text
        }
    }
    return post(loja_id, json=payload)


@celery_app.task(bind=True, soft_time_limit=7)
def send_quickreply_message(self, sender_id, loja_id, text, quick_replies, icon=ROBOT_ICON):
    if icon:
        payload_text = icon + ': ' + text
    else:
        payload_text = text
    payload = {
        'recipient': {
            'id': sender_id
        },
        'message': {
            'text': payload_text,
            'quick_replies': quick_replies
        }
    }
    return post(loja_id, json=payload)


@celery_app.task(bind=True, soft_time_limit=7)
def send_generic_message(self, sender_id, loja_id, elements):
    payload = {
        'recipient': {
            'id': sender_id
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': elements
                }
            }
        }
    }
    return post(loja_id, json=payload)


def get_elements_menu(conversa):
    menu = []
    possui_itens_pedido = (len(conversa['itens_pedido']) > 0)
    mesa_definida = (conversa['mesa'] is not None)
    pedido_andamento = (conversa['datahora_inicio_pedido'] is not None)
    if possui_itens_pedido and mesa_definida and pedido_andamento:
        menu.append(
            {
                'title': u'Envie seu pedido',
                'image_url': 'https://sistema.marviin.com.br/static/marviin/img/enviar_pedido.jpg',
                'subtitle': u'Envie seu pedido para iniciarmos seu preparo.',
                'buttons': [
                    {
                        'type': 'postback',
                        'title': u'Enviar pedido',
                        'payload': 'finalizar_pedido'
                    }
                ]
            })
    if mesa_definida and pedido_andamento:
        menu.append(
            {
                'title': u'Adicione itens ao pedido',
                'image_url': 'https://sistema.marviin.com.br/static/marviin/img/adicionar_itens.jpg',
                'subtitle': u'Adicione itens ao pedido que você já começou a montar.',
                'buttons': [
                    {
                        'type': 'postback',
                        'title': u'+ itens ao pedido',
                        'payload': 'pedir_mais'
                    }
                ]
            })
    if possui_itens_pedido and mesa_definida and pedido_andamento:
        menu.append(
            {
                'title': u'Atualize seu pedido',
                'image_url': 'https://sistema.marviin.com.br/static/marviin/img/atualizar_pedido.jpg',
                'subtitle': u'Atualize os itens já adicionados ao seu pedido.',
                'buttons': [
                    {
                        'type': 'postback',
                        'title': u'Atualizar pedido',
                        'payload': 'menu_rever_pedido'
                    }
                ]
            })
    menu.append(
        {
            'title': u'Realize um novo pedido',
            'image_url': 'https://sistema.marviin.com.br/static/marviin/img/novo-pedido.jpg',
            'subtitle': u'Monte um novo pedido por aqui, é bem fácil.',
            'buttons': [
                {
                    'type': 'postback',
                    'title': u'Novo pedido',
                    'payload': 'menu_novo_pedido'
                }
            ]
        })
    menu.append(
        {
            'title': u'Peça o cardápio',
            'image_url': 'https://sistema.marviin.com.br/static/marviin/img/pedir-cardapio.jpg',
            'subtitle': u'Peça nosso cardápio para auxiliá-lo(a) na montagem de seu pedido.',
            'buttons': [
                {
                    'type': 'postback',
                    'title': u'Pedir cardápio',
                    'payload': 'pedir_cardapio'
                }
            ]
        })
    menu.append(
        {
            'title': u'Chame o garçom',
            'image_url': 'https://sistema.marviin.com.br/static/marviin/img/chamar-garcom.jpg',
            'subtitle': u'Precisando de ajuda, pode deixar que peço para ele(a) ir aí.',
            'buttons': [
                {
                    'type': 'postback',
                    'title': u'Chamar garçom',
                    'payload': 'chamar_garcom'
                }
            ]
        })
    menu.append(
        {
            'title': u'Peça a conta',
            'image_url': 'https://sistema.marviin.com.br/static/marviin/img/atualizar_pedido.jpg',
            'subtitle': u'Quando estiver satisfeito(a) deixa que eu peço para trazerem sua conta.',
            'buttons': [
                {
                    'type': 'postback',
                    'title': u'Pedir a conta',
                    'payload': 'pedir_conta'
                }
            ]
        })
    '''
    menu.append(
        {
            'content_type': 'text',
            'title': u'Ajuda',
            'payload': 'menu_ajuda'
        })
    '''
    return menu


def get_quickreply_cardapio_digital(conversa):
    menu = []
    possui_itens_pedido = (len(conversa['itens_pedido']) > 0)
    mesa_definida = (conversa['mesa'] is not None)
    pedido_andamento = (conversa['datahora_inicio_pedido'] is not None)
    if possui_itens_pedido and mesa_definida and pedido_andamento:
        menu.append(
            {
                'content_type': 'text',
                'title': u'Enviar pedido',
                'payload': 'finalizar_pedido'
            })
    if mesa_definida and pedido_andamento:
        menu.append(
            {
                'content_type': 'text',
                'title': u'+ itens ao pedido',
                'payload': 'pedir_mais'
            })
    if possui_itens_pedido and mesa_definida and pedido_andamento:
        menu.append(
            {
                'content_type': 'text',
                'title': u'Atualizar pedido',
                'payload': 'menu_rever_pedido'
            })
    menu.append(
        {
            'content_type': 'text',
            'title': u'Novo pedido',
            'payload': 'menu_novo_pedido'
        })
    menu.append(
        {
            'content_type': 'text',
            'title': u'Voltar ao menu',
            'payload': 'voltar_menu'
        })
    return menu


def get_quickreply_pedido():
    return [
        {
            'content_type': 'text',
            'title': u'Enviar pedido',
            'payload': 'finalizar_pedido'
        },
        {
            'content_type': 'text',
            'title': u'Pedir mais coisas',
            'payload': 'pedir_mais'
        },
        {
            'content_type': 'text',
            'title': u'Atualizar pedido',
            'payload': 'menu_rever_pedido'
        },
        {
            'content_type': 'text',
            'title': u'Voltar ao menu',
            'payload': 'voltar_menu'
        }
    ]


def get_quickreply_pedido2():
    return [
        {
            'content_type': 'text',
            'title': u'Pedir mais coisas',
            'payload': 'pedir_mais'
        },
        {
            'content_type': 'text',
            'title': u'Atualizar pedido',
            'payload': 'menu_rever_pedido'
        },
        {
            'content_type': 'text',
            'title': u'Enviar pedido',
            'payload': 'finalizar_pedido'
        },
        {
            'content_type': 'text',
            'title': u'Começar novo pedido',
            'payload': 'menu_novo_pedido2'
        },
        {
            'content_type': 'text',
            'title': u'Voltar ao menu',
            'payload': 'voltar_menu'
        }
    ]


def get_quickreply_finalizar_pedido():
    return [
        {
            'content_type': 'text',
            'title': u'Confirmar envio',
            'payload': 'finalizar_enviar'
        },
        {
            'content_type': 'text',
            'title': u'Pedir mais coisas',
            'payload': 'pedir_mais'
        },
        {
            'content_type': 'text',
            'title': u'Atualizar pedido',
            'payload': 'menu_rever_pedido'
        },
        {
            'content_type': 'text',
            'title': u'Começar novo pedido',
            'payload': 'menu_novo_pedido2'
        },
        {
            'content_type': 'text',
            'title': u'Voltar ao menu',
            'payload': 'voltar_menu'
        }
    ]


def get_quickreply_atualizar_pedido():
    return [
        {
            'content_type': 'text',
            'title': u'Voltar',
            'payload': 'menu_rever_pedido'
        },
        {
            'content_type': 'text',
            'title': u'Voltar ao menu',
            'payload': 'voltar_menu'
        }
    ]


def get_quickreply_voltar_menu():
    return [
        {
            'content_type': 'text',
            'title': u'Voltar ao menu',
            'payload': 'voltar_menu'
        }
    ]


def get_quickreply_conversa_suspensa():
    return [
        {
            'content_type': 'text',
            'title': u'Finalizar contato',
            'payload': 'sair_suspensao'
        }
    ]


def get_quickreply_sim_nao():
    return [
        {
            'content_type': 'text',
            'title': u'Sim',
            'payload': 'sim'
        },
        {
            'content_type': 'text',
            'title': u'Não',
            'payload': 'nao'
        },
        {
            'content_type': 'text',
            'title': u'Voltar ao menu',
            'payload': 'voltar_menu'
        }
    ]


def get_quickreply_cardapio():
    return [
        {
            'content_type': 'text',
            'title': u'Digital',
            'payload': 'cardapio_digital'
        },
        {
            'content_type': 'text',
            'title': u'Impresso',
            'payload': 'cardapio_impresso'
        },
        {
            'content_type': 'text',
            'title': u'Voltar ao menu',
            'payload': 'voltar_menu'
        }
    ]


def get_mensagem(id_mensagem, **args):
    mensagens = {
        'ola':        Template(u'Olá $arg1, como posso ajudá-lo(a)?'),
        'getstarted': Template(u'Legal, $arg1, vamos começar. Navegue lateralmente pelas opções abaixo, e veja como '
                               u'posso ajudá-lo(a).'),
        'menu':       Template(u'Digite a palavra menu para saber em como posso ajudá-lo(a). '
                               u'Você poderá digitá-la novamente a qualquer momento.'),
        'mesa':       Template(u'Por favor, digite sua mesa.'),
        'pedido':     Template(u'Excelente, digite aqui o que deseja, quanto mais detalhado melhor! ;)'),
        'pedido1':    Template(u'Exemplo: 1 água com gelo sem limão'),
        'pedido2':    Template(u'Desculpe, mas não encontrei um pedido sendo montado. Pedirei que comece um novo, por '
                               u'favor. Obrigado.'),
        'anotado':    Template(u'Anotado.\n$arg1, deseja mais alguma coisa ou posso enviar seu pedido?'),
        'anotado1':   Template(u'Pedido atualizado.\nDeseja mais alguma coisa ou posso enviar seu pedido?'),
        'qtde':       Template(u'$arg1\nPerdoe-me, mas não consegui identificar a quantidade do(s) seguinte(s) '
                               u'item(ns) acima.'),
        'qtde1':      Template(u'Peço, por favor, que reenvie sua última mensagem corrigindo-os.'),
        'enviar':     Template(u'Maravilha, já já seu pedido estará aí.\nPosso ajudá-lo(a) em algo mais?'),
        'agradeco':   Template(u'Eu que agradeço.'),
        'robo':       Template(u'Desculpe, mas não entendi o que deseja. \nComo posso auxiliá-lo(a)?'),
        'anotado2':   Template(u'Por favor, escolha uma das opções que lhe apresento abaixo.'),
        'mesa3':      Template(u'Certo, providenciarei que seus pedidos sejam enviados para esta mesa $arg1.'),
        'mesa4':      Template(u'Mesa anterior igual a atual.'),
        'mesa5':      Template(u'Mesa $arg1, correto?'),
        'sim_nao':    Template(u'Escolha uma das opções abaixo, por favor.'),
        'pedido3':    Template(u'Por favor, pode digitar. :)'),
        'pedido4':    Template(u'$arg1, já existe um pedido sendo montado. Deseja continuar este pedido ou começar um '
                               u'novo?'),
        'rever2':     Template(u'Pedido se encontra vazio de itens. Como posso auxiliá-lo(a)?'),
        'auxilio':    Template(u'Em que posso ajudá-lo(a)?'),
        'auxilio1':   Template(u'Em que posso ajudá-lo(a) agora?'),
        'auxilio2':   Template(u'Anotado. Como posso ajudá-lo(a) agora?'),
        'desenv':     Template(u'Função em desenvolvimento...'),
        'finalizar':  Template(u'Segue, acima, seu pedido para conferência. Confirma o envio?'),
        'cardapio':   Template(u'Já levaremos o cardápio para você. Em que posso ajudá-lo(a) agora?'),
        'cardapio2':  Template(u'Deseja a versão digital ou quer que lhe traga o impresso?'),
        'cardapio3':  Template(u'Segue, acima, imagem do cardápio.'),
        'cardapio4':  Template(u'Seguem, acima, 2 imagens do cardápio.'),
        'cardapio5':  Template(u'Desculpe, ficarei devendo a versão digital, mas já pedi para trazerem o cardápio '
                               u'impresso para você. Em que posso ajudá-lo(a) agora?'),
        'garcom':     Template(u'Perfeito, logo logo ele(a) estará aí. Como posso ajudá-lo(a) agora?'),
        'suspensao':  Template(u'Sua resposta foi enviada.\nPara finaizar o contato clique abaixo.'),
        'conta':      Template(u'Ok, já avisei para trazerem sua conta.\nMuito obrigado(a), espero que sua experiência '
                               u'tenha sido a melhor possível.\nVolte sempre!'),
        'conta2':     Template(u'Desculpe, mas não tenho anotado sua mesa. Você poderia me informar, por favor.'),
    }
    return mensagens[id_mensagem].substitute(args)


def define_mesa(mesa, conversa):
    if conversa['mesa'] is None:
        conversa['mesa'] = []
        conversa['mesa'].append('')
    elif len(conversa['mesa']) == 2:
        conversa['mesa'][1] = conversa['mesa'][0]
    elif len(conversa['mesa']) == 1:
        conversa['mesa'].append(conversa['mesa'][0])
    conversa['mesa'][0] = mesa
    return True


def anota_pedido(message, conversa, i_edicao=None):
    pedido = estrutura_pedido(message)
    app_log.debug('=========================>>>>> 3 ' + repr(conversa['itens_pedido']))
    if i_edicao is not None:
        del conversa['itens_pedido'][int(i_edicao)]
    conversa['itens_pedido'] += pedido
    app_log.debug('=========================>>>>> 4 ' + repr(conversa['itens_pedido']))
    return True


def estrutura_pedido(message):
    pedido = []
    app_log.debug('=========================>>>>> 1 ' + repr(pedido))
    itens_pedido = message.splitlines()
    for item_linha in itens_pedido:
        itens = item_linha.split(';')
        for item in itens:
            if len(item.strip()) == 0:
                continue
            app_log.debug('=========================>>>>> 2 ' + item)
            item_pedido = item.strip().split(' ', 1)
            quantidade = [int(qtde) for qtde in [item_pedido[0]] if qtde.isdigit()]
            if len(quantidade) == 0 or (quantidade[0] > 0 and len(item_pedido) == 1):
                pedido.append({
                    'descricao': item,
                    'quantidade': 1
                })
            elif quantidade[0] > 0:
                pedido.append({
                    'descricao': item_pedido[1],
                    'quantidade': quantidade[0]
                })
    return pedido


@celery_app.task(bind=True, soft_time_limit=10)
def get_cardapio(self, loja_id):
    data = {}
    pass
    data['chave_bot_api_interna'] = CHAVE_BOT_API_INTERNA
    data['id_loja_fb'] = loja_id
    url = 'http://localhost:8888/marviin/api/rest/cardapio'
    response = requests.get(url, auth=(SUPER_USER_USER, SUPER_USER_PASSWORD), params=data)
    json_response = response.json()
    app_log.debug(repr(json_response))
    if json_response['success']:
        if len(json_response['cardapio']) > 0:
            return json_response['cardapio']
    return None


@celery_app.task(bind=True, soft_time_limit=10)
def touch_cliente(self, sender_id):
    data = {}
    pass
    data['chave_bot_api_interna'] = CHAVE_BOT_API_INTERNA
    url = 'http://localhost:8888/marviin/api/rest/cliente/' + sender_id + '/touch'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(SUPER_USER_USER + ':' + SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    app_log.debug(repr(response))


@celery_app.task(bind=True, soft_time_limit=10)
def salva_se_nao_existir(self, sender_id, user):
    data = {}
    pass
    data['chave_bot_api_interna'] = CHAVE_BOT_API_INTERNA
    data['id_cliente'] = sender_id
    data['nome_cliente'] = user['first_name'] + ' ' + user['last_name']
    data['foto_cliente'] = user['profile_pic']
    data['genero'] = user['gender']
    url = 'http://localhost:8888/marviin/api/rest/cliente'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(SUPER_USER_USER + ':' + SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    app_log.debug(repr(response))


@celery_app.task(bind=True, soft_time_limit=10)
def enviar_pedido(self, sender_id, loja_id, conversa):
    if conversa['mesa'] is None:
        return
    data = {}
    pass
    data['chave_bot_api_interna'] = CHAVE_BOT_API_INTERNA
    data['id_loja'] = loja_id
    data['origem'] = 'fbmessenger'
    data['id_cliente'] = sender_id
    data['nome_cliente'] = conversa['usuario']['first_name'] + ' ' + conversa['usuario']['last_name']
    data['foto_cliente'] = conversa['usuario']['profile_pic']
    data['itens_pedido'] = conversa['itens_pedido']
    data['mesa'] = conversa['mesa'][0]
    url = 'http://localhost:8888/marviin/api/rest/pedido'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(SUPER_USER_USER + ':' + SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    app_log.debug(repr(response))


def resposta_dashboard(message=None, payload=None, sender_id=None, loja_id=None, conversa=None):
    if unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() == u'menu' or \
                    payload == 'sair_suspensao':
        passo_finalizar_contato(sender_id, loja_id, conversa)
    else:
        send_quickreply_message.delay(sender_id, loja_id, get_mensagem('suspensao'),
                                      get_quickreply_conversa_suspensa())
        envia_resposta.delay(conversa, loja_id, sender_id, message)


@celery_app.task(bind=True, soft_time_limit=10)
def envia_resposta(self, conversa, loja_id, sender_id, message):
    data = {}
    pass
    data['chave_bot_api_interna'] = CHAVE_BOT_API_INTERNA
    data['id_loja'] = loja_id
    data['id_cliente'] = sender_id
    data['origem'] = 'chat'
    data['nome_cliente'] = conversa['usuario']['first_name'] + ' ' + conversa['usuario']['last_name']
    data['foto_cliente'] = conversa['usuario']['profile_pic']
    data['cliente'] = message
    data['uid'] = conversa['uid']
    url = 'http://localhost:8888/marviin/api/rest/mensagem_bot'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(SUPER_USER_USER + ':' + SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    app_log.debug(repr(response))


@celery_app.task(bind=True, soft_time_limit=10)
def troca_mesa_dashboard(self, sender_id, loja_id, conversa):
    data = {}
    pass
    data['chave_bot_api_interna'] = CHAVE_BOT_API_INTERNA
    data['id_loja'] = loja_id
    data['id_cliente'] = sender_id
    data['mesa'] = conversa['mesa'][0]
    if len(conversa['mesa']) == 2:
        data['mesa_anterior'] = conversa['mesa'][1]
    url = 'http://localhost:8888/marviin/api/rest/troca_mesa'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(SUPER_USER_USER + ':' + SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    app_log.debug(repr(response))


@celery_app.task(bind=True, soft_time_limit=10)
def notificacao_dashboard(self, sender_id, loja_id, conversa, metodo_api):
    data = {}
    pass
    data['chave_bot_api_interna'] = CHAVE_BOT_API_INTERNA
    data['id_loja'] = loja_id
    data['id_cliente'] = sender_id
    data['nome_cliente'] = conversa['usuario']['first_name'] + ' ' + conversa['usuario']['last_name']
    data['foto_cliente'] = conversa['usuario']['profile_pic']
    data['mesa'] = conversa['mesa'][0]
    url = 'http://localhost:8888/marviin/api/rest/pede_'+metodo_api
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(SUPER_USER_USER + ':' + SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    app_log.debug(repr(response))


def set_variaveis(conversa, nao_entendidas=(True, 0), itens_pedido=(True, None),
                  datetime_pedido=(True, None)):
    if datetime_pedido[0]:
        conversa['datahora_inicio_pedido'] = datetime_pedido[1]
    if nao_entendidas[0]:
        conversa['nao_entendidas'] = nao_entendidas[1]
    if itens_pedido[0]:
        conversa['itens_pedido'] = [] if not itens_pedido[1] else itens_pedido[1]


def checa_duplicidade(sender_id, loja_id, timestamp, conversa):
    duplicado = False
    if conversa['entry'] is None:
        conversa['entry'] = {}
    elif conversa['entry']['sender_id'] == sender_id and \
            conversa['entry']['loja_id'] == loja_id and \
            conversa['entry']['timestamp'] == timestamp:
        duplicado = True
    conversa['entry']['sender_id'] = sender_id
    conversa['entry']['loja_id'] = loja_id
    conversa['entry']['timestamp'] = timestamp
    return duplicado


@flask_app.route('/', defaults={'path': ''})
@flask_app.route('/.well-known/acme-challenge/<path:path>')
def ping(path):
    return send_from_directory('.well-known/acme-challenge', path, as_attachment=False,
                               mimetype='text/plain')


@celery_app.task(bind=True, soft_time_limit=1, default_retry_delay=0, max_retries=3)
def teste_tarefa(self):
    try:
        app_log.debug('>>> tarefa iniciada ::')
        time.sleep(4)
        app_log.debug('>>> tarefa concluida ::')
    except SoftTimeLimitExceeded as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True)
def error_handler(self, uuid):
    result = self.app.AsyncResult(uuid)
    app_log.debug('Task {0} raised exception: {1!r}\n{2!r}'.format(
          uuid, result.result, result.traceback))


@flask_app.route("/teste_tarefa", methods=['GET', 'POST'])
def teste_tarefa_route():
    app_log.debug('>>> inicio requisicao ::')
    teste_tarefa.apply_async((), link_error=error_handler.s())
    resp = Response('success', status=200, mimetype='text/plain')
    resp.status_code = 200
    app_log.debug('>>> fim requisicao ::')
    return resp


@contextmanager
def sender_lock(sender_id):
    app_log.debug('lock acquire:: ' + sender_id)
    lock = cache.add(sender_id + 'lock', True, time=EXPIRACAO_CACHE_LOCK)
    app_log.debug('lock:: ' + repr(lock) + ' :: ' + sender_id)
    yield lock
    if lock:
        cache.delete(sender_id + 'lock')
        app_log.debug('lock released:: ' + sender_id)
    else:
        app_log.debug('no lock ' + sender_id)


def atualiza_cardapio(loja_id, cardapio):
    app_log.debug('atualiza_cardapio:: ' + repr(cardapio))
    if cardapio is None:
        cache.delete(loja_id + 'cardapio')
    else:
        cache.set(loja_id + 'cardapio', cardapio, time=EXPIRACAO_CACHE_LOJA)


@flask_app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == CHAVE_BOT_WEBHOOK:
            return request.args.get("hub.challenge")
        return
    if request.method == 'POST':
        app_log.debug(u'INICIO POST :: ')
        output = request.json
        app_log.debug(output)
        entry = output['entry'][0]
        if 'messaging' not in entry:
            resp = Response('success', status=200, mimetype='text/plain')
            resp.status_code = 200
            return resp
        event = entry['messaging']
        for x in event:
            if x.get('message') and x['message'].get('is_echo'):
                resp = Response(u'mensagem de echo', status=200, mimetype='text/plain')
                resp.status_code = 200
                return resp
            sender_id = None
            loja_id = None
            if x.get('sender') and x['sender']['id'] and x.get('recipient') and x['recipient']['id']:
                sender_id = str(x['sender']['id'])
                loja_id = str(x['recipient']['id'])
                app_log.debug('sender_id:: ' + sender_id)
                app_log.debug('loja_id:: ' + loja_id)
            if sender_id is None or loja_id is None:
                resp = Response(u'sender e/ou recipient não encontrado', status=200, mimetype='text/plain')
                resp.status_code = 200
                return resp
            else:
                with sender_lock(sender_id) as lock:
                    if lock:
                        app_log.debug('lock acquired:: ' + sender_id)
                        touch_cliente.delay(sender_id)
                        conversa = cache.get(sender_id)
                        app_log.debug('alguma conversa no cache:: ' + repr(conversa))
                        if conversa is not None:
                            cache.set(sender_id, conversa, time=EXPIRACAO_CACHE_CONVERSA)
                            app_log.debug('conversa:: ' + repr(conversa))
                        else:
                            user = pega_usuario(sender_id, loja_id)
                            if not user:
                                resp = Response(u'não foi possível recuperar o usuário do facebook', status=200,
                                                mimetype='text/plain')
                                resp.status_code = 200
                                return resp
                            conversa = {
                                'passo': 0,
                                'passo_sim': None,
                                'passo_nao': None,
                                'usuario': user,
                                'mesa': None,
                                'aux': None,
                                'itens_pedido': [],
                                'nao_entendidas': 0,
                                'datahora_inicio_pedido': None,
                                'suspensa': 0,
                                'uid': None,
                                'entry': None,
                            }
                            app_log.debug('usuario:: ' + repr(user))
                        if x.get('message') or x.get('postback'):
                            if checa_duplicidade(sender_id, loja_id, x['timestamp'], conversa):
                                resp = Response(u'chamada duplicada', status=200,
                                                mimetype='text/plain')
                                resp.status_code = 200
                                return resp
                            if x.get('message') and x['message'].get('text') and not x['message'].get('quick_reply'):
                                message = x['message']['text'].strip()
                                app_log.debug('message: '+message)
                                if conversa['suspensa'] > 0:
                                    resposta_dashboard(message=message, sender_id=sender_id, loja_id=loja_id,
                                                       conversa=conversa)
                                elif unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() \
                                        in saudacao:
                                    conversa['passo'] = 0
                                    passo_ola(message, sender_id, loja_id, conversa)
                                elif u'inicio' in unicodedata.normalize('NFKD', message) \
                                        .encode('ASCII', 'ignore').lower():
                                    passo_inicio(sender_id, loja_id, conversa)
                                elif u'menu' in unicodedata.normalize('NFKD', message)\
                                        .encode('ASCII', 'ignore').lower():
                                    conversa['passo'] = 1
                                    passo_menu(message, sender_id, loja_id, conversa)
                                elif u'pedido' in unicodedata.normalize('NFKD', message)\
                                        .encode('ASCII', 'ignore').lower():
                                    # passos 13 e 14 definidos dentro do método
                                    passo_novo_pedido(message, sender_id, loja_id, conversa)
                                elif unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() \
                                        in agradecimentos:
                                    conversa['passo'] = 11
                                    passo_agradecimento(message, sender_id, loja_id, conversa)
                                else:
                                    define_passo(message, sender_id, loja_id, conversa, conversa['passo'])
                            elif ((x.get('message') and x['message'].get('quick_reply') and
                                   x['message']['quick_reply'].get('payload')) or
                                  (x.get('postback') and x['postback'].get('payload'))):
                                if x.get('message'):
                                    payload = x['message']['quick_reply']['payload']
                                    message = x['message']['text']
                                else:
                                    payload = x['postback'].get('payload')
                                    message = next(v for k, v in POSTBACK_MAP.items() if payload.startswith(k))
                                app_log.debug(payload)
                                conversa['suspensa'] = 0
                                define_payload(message, sender_id, loja_id, conversa, payload)
                        elif x.get('dashboard'):
                            conversa['suspensa'] += 1
                            conversa['uid'] = x['dashboard']['uid']
                            send_text_message.delay(sender_id, loja_id, x['dashboard']['message'], icon=u'\U0001f464')
                        cache.set(sender_id, conversa, time=EXPIRACAO_CACHE_CONVERSA)
        resp = Response('success', status=200, mimetype='text/plain')
        resp.status_code = 200
        return resp


def define_payload(message, sender_id, loja_id, conversa, payload):
    if payload == 'menu_novo_pedido' or payload == 'menu_novo_pedido2':
        if payload == 'menu_novo_pedido2':
            set_variaveis(conversa)
        # passos 13 e 14 definidos dentro do método
        passo_novo_pedido(message, sender_id, loja_id, conversa)
    elif payload == 'menu_trocar_mesa':
        define_sim_nao(conversa, 3, define_passo, 15, define_payload, 'menu_trocar_mesa')
        passo_trocar_mesa_2(message, sender_id, loja_id, conversa)
    elif payload == 'menu_rever_pedido':
        conversa['passo'] = 16
        passo_rever_pedido_2(message, sender_id, loja_id, conversa)
    elif payload.startswith('editar_item_'):
        conversa['passo'] = 28
        passo_editar_item(message, sender_id, loja_id, conversa, payload[len('editar_item_'):])
    elif payload.startswith('remover_item_'):
        # passos 29 e 31 definidos dentro do método
        passo_remover_item(message, sender_id, loja_id, conversa, payload[len('remover_item_'):])
    elif payload.startswith('vermais_offset_'):
        conversa['passo'] = 30
        conversa['aux'] = int(payload[len('vermais_offset_'):])
        passo_rever_pedido_2(message, sender_id, loja_id, conversa, offset=conversa['aux'])
    elif payload == 'pedir_conta':
        # passos 24 e 25 definidos dentro do método
        passo_pedir_conta(message, sender_id, loja_id, conversa)
    elif payload == 'pedir_mais':
        conversa['passo'] = 17
        passo_pedir_mais(message, sender_id, loja_id, conversa)
    elif payload == 'finalizar_pedido':
        conversa['passo'] = 18
        passo_finalizar_pedido(message, sender_id, loja_id, conversa)
    elif payload == 'finalizar_enviar':
        conversa['passo'] = 0
        passo_finalizar_enviar(message, sender_id, loja_id, conversa)
    elif payload == 'pedir_cardapio':
        # passos 3, 19, 20, 26 e 27 utilizados nesta ação
        passo_pedir_cardapio(message, sender_id, loja_id, conversa)
    elif payload == 'chamar_garcom':
        # passos 22 e 23 definidos dentro do método
        passo_chamar_garcom(message, sender_id, loja_id, conversa)
    elif payload == 'voltar_menu':
        conversa['passo'] = 1
        conversa['aux'] = None
        conversa['passo_sim'] = None
        conversa['passo_nao'] = None
        passo_menu(message, sender_id, loja_id, conversa)
    elif payload == 'sim':
        conversa['passo_sim'][0](message, sender_id, loja_id, conversa, conversa['passo_sim'][1])
        conversa['passo_sim'] = None
        conversa['passo_nao'] = None
    elif payload == 'nao':
        conversa['passo_nao'][0](message, sender_id, loja_id, conversa, conversa['passo_nao'][1])
    elif payload == 'cardapio_impresso':
        passo_cardapio_impresso(message, sender_id, loja_id, conversa)
    elif payload == 'cardapio_digital':
        passo_cardapio_digital(message, sender_id, loja_id, conversa)
    elif payload == 'menu_get_started':
        passo_inicio(sender_id, loja_id, conversa)


def passo_inicio(sender_id, loja_id, conversa):
    conversa['passo'] = 0
    bot1 = get_mensagem('getstarted', arg1=conversa['usuario']['first_name'])
    chain(send_text_message.si(sender_id, loja_id, bot1),
          send_generic_message.si(sender_id, loja_id, get_elements_menu(conversa)))()


def define_sim_nao(conversa, passo, passo_sim_func, passo_sim_var, passo_nao_func, passo_nao_var):
    conversa['passo'] = passo
    conversa['passo_sim'] = []
    conversa['passo_sim'].append(passo_sim_func)
    conversa['passo_sim'].append(passo_sim_var)
    conversa['passo_nao'] = []
    conversa['passo_nao'].append(passo_nao_func)
    conversa['passo_nao'].append(passo_nao_var)


def define_passo(message, sender_id, loja_id, conversa, passo):
    conversa['passo'] = passo
    if passo == 3:
        conversa['passo'] = 26
        conversa['aux'] = message
        passo_confirma_mesa(message, sender_id, loja_id)
    elif passo == 15:
        conversa['passo'] = 2
        passo_trocar_mesa(message, sender_id, loja_id, conversa)
    elif passo == 13:
        # passos 6 definido dentro do método
        passo_um(message, sender_id, loja_id, conversa)
    elif passo == 6 or passo == 9 or passo == 14 or passo == 17:
        # passos 8 e 9 definidos dentro do método
        passo_dois(message, sender_id, loja_id, conversa)
    elif passo == 8:
        conversa['passo'] = 10
        passo_tres(message, sender_id, loja_id, conversa)
    elif passo == 18:
        if u'nao' in unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower():
            conversa['passo'] = 21
            passo_menu(message, sender_id, loja_id, conversa)
        elif u'sim' in unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() or \
             u'pode' in unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() or \
             u'confirm' in unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower():
            conversa['passo'] = 0
            passo_finalizar_enviar(message, sender_id, loja_id, conversa)
        elif u'editar' in unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower():
            conversa['passo'] = 16
            passo_rever_pedido_2(message, sender_id, loja_id, conversa)
    elif passo == 19:
        define_mesa(conversa['aux'], conversa)
        conversa['aux'] = None
        passo_cardapio_impresso(message, sender_id, loja_id, conversa)
    elif passo == 22:
        passo_mesa_dependencia(message, sender_id, loja_id, conversa, 'garcom', 23)
    elif passo == 25:
        passo_mesa_dependencia(message, sender_id, loja_id, conversa, 'conta', 24)
    elif passo == 26 or passo == 29:
        normalizada = unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower()
        if u'sim' == normalizada:
            conversa['passo_sim'][0](message, sender_id, loja_id, conversa, conversa['passo_sim'][1])
            conversa['passo_sim'] = None
            conversa['passo_nao'] = None
        elif u'nao' == normalizada:
            conversa['passo_nao'][0](message, sender_id, loja_id, conversa, conversa['passo_nao'][1])
        else:
            bot = get_mensagem('sim_nao')
            send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_sim_nao())
    elif passo == 28 or passo == 31:
        if pre_requisito_pedido(sender_id, loja_id, conversa):
            if passo == 28:
                anota_pedido(message, conversa, i_edicao=conversa['aux'])
            else:
                del conversa['itens_pedido'][int(conversa['aux'])]
            conversa['passo'] = 16
            set_variaveis(conversa,
                          itens_pedido=(False, None),
                          datetime_pedido=(False, None))
            passo_rever_pedido_2(message, sender_id, loja_id, conversa, eh_msg_sucesso=True)
    else:
        conversa['passo'] = 12
        passo_nao_entendido(message, sender_id, loja_id, conversa)


def pega_usuario(sender_id, loja_id):
    retries = 0
    user = None
    while retries < 1:
        try:
            app_log.debug('pega_usuario 1:: ')
            user = get_object.delay(sender_id, loja_id).get()
            salva_se_nao_existir.delay(sender_id, user)
            app_log.debug('pega_usuario 2:: ')
            break
        except SoftTimeLimitExceeded:
            retries += 1
            app_log.debug('pega_usuario 3:: ')
        except Exception as e:
            retries += 1
            app_log.debug('pega_usuario 4:: '+repr(e))
    app_log.debug('pega_usuario 5:: ')
    return user


def passo_finalizar_contato(sender_id, loja_id, conversa):
    if conversa['passo'] == 0 or conversa['passo'] == 1 or conversa['passo'] == 2 or conversa['passo'] == 5 \
            or conversa['passo'] == 20 or conversa['passo'] == 21 or conversa['passo'] == 23 or conversa['passo'] == 24:
        passo_menu(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 3:
        mensagem_mesa(conversa, loja_id, sender_id)
    elif conversa['passo'] == 15:
        passo_trocar_mesa_2(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 16:
        passo_rever_pedido_2(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 13:
        passo_novo_pedido(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 6 or conversa['passo'] == 9 or conversa['passo'] == 14 or conversa['passo'] == 17:
        mensagem_pedido(sender_id, loja_id, conversa)
    elif conversa['passo'] == 8:
        bot = get_mensagem('anotado', arg1=conversa['usuario']['first_name'])
        send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_pedido())
    elif conversa['passo'] == 10:
        passo_tres(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 18:
        passo_finalizar_pedido(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 19:
        passo_pedir_cardapio(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 25:
        passo_pedir_conta(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 27:
        passo_cardapio(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 28:
        passo_editar_item(None, sender_id, loja_id, conversa, conversa['aux'])
    elif conversa['passo'] == 29:
        passo_remover_item(None, sender_id, loja_id, conversa, conversa['aux'])
    elif conversa['passo'] == 30:
        passo_rever_pedido_2(None, sender_id, loja_id, conversa, offset=conversa['aux'])
    conversa['suspensa'] = 0


def existe_pedido_andamento(sender_id, loja_id, conversa):
    if conversa['datahora_inicio_pedido'] is not None and len(conversa['itens_pedido']) > 0:
        bot = get_mensagem('pedido4', arg1=conversa['usuario']['first_name'])
        send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_pedido2())
        return True
    return False


def passo_editar_item(message, sender_id, loja_id, conversa, i):
    if pre_requisito_pedido(sender_id, loja_id, conversa):
        conversa['aux'] = i
        item = repr(conversa['itens_pedido'][int(i)]['quantidade']) + ' ' + \
               conversa['itens_pedido'][int(i)]['descricao']
        bot = u'Digite seu pedido'
        chain(send_text_message.si(sender_id, loja_id, item, icon=None),
              send_quickreply_message.si(sender_id, loja_id, bot, get_quickreply_atualizar_pedido()))()


def passo_remover_item(message, sender_id, loja_id, conversa, i):
    if pre_requisito_pedido(sender_id, loja_id, conversa):
        conversa['aux'] = i
        item = repr(conversa['itens_pedido'][int(i)]['quantidade']) + ' ' + \
               conversa['itens_pedido'][int(i)]['descricao']
        bot = u'Remove o item acima?'
        define_sim_nao(conversa, 29, define_passo, 31, define_payload, 'menu_rever_pedido')
        chain(send_text_message.si(sender_id, loja_id, item, icon=None),
              send_quickreply_message.si(sender_id, loja_id, bot, get_quickreply_sim_nao()))()


def pre_requisito_pedido(sender_id, loja_id, conversa):
    if conversa['datahora_inicio_pedido'] is None:
        conversa['passo'] = 0
        chain(send_text_message.si(sender_id, loja_id, get_mensagem('pedido2')),
              send_generic_message.si(sender_id, loja_id, get_elements_menu(conversa)))()
        return False
    return True


def passo_cardapio_impresso(message, sender_id, loja_id, conversa, texto_id=None):
    if conversa['mesa'] is None:
        define_sim_nao(conversa, 3, define_passo, 19, define_payload, 'cardapio_impresso')
        mensagem_mesa(conversa, loja_id, sender_id)
    else:
        conversa['passo'] = 20
        mensagem_sucesso(sender_id, loja_id, conversa, (texto_id if texto_id else 'cardapio'))


def passo_cardapio_digital(message, sender_id, loja_id, conversa):
    cardapios = cache.get(loja_id + 'cardapio')
    conversa['passo'] = 0
    tarefas = []
    for cardapio in cardapios:
        app_log.debug('cardapio digital:: ' + repr(cardapio))
        tarefas.append(send_image_url_message.si(sender_id, loja_id, cardapio))
    if len(cardapios) == 1:
        bot = get_mensagem('cardapio3')
    else:
        bot = get_mensagem('cardapio4')
    tarefas.append(send_quickreply_message.si(sender_id, loja_id, bot, get_quickreply_cardapio_digital(conversa)))
    chain(tarefas)()


def passo_cardapio(message, sender_id, loja_id, conversa):
    app_log.debug('passo_cardapio 1:: ')
    try:
        cardapio = get_cardapio.delay(loja_id).get()
        app_log.debug('passo_cardapio 2:: ' + repr(cardapio))
        atualiza_cardapio(loja_id, cardapio)
        if cardapio is None:
            app_log.debug('passo_cardapio 3:: ')
            passo_cardapio_impresso(message, sender_id, loja_id, conversa)
        else:
            conversa['passo'] = 27
            bot = get_mensagem('cardapio2')
            send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_cardapio())
    except SoftTimeLimitExceeded:
        app_log.debug('passo_cardapio 4:: ')
        passo_cardapio_impresso(message, sender_id, loja_id, conversa, texto_id='cardapio5')
    except Exception as e:
        app_log.debug('passo_cardapio 5:: ' + repr(e))
        passo_cardapio_impresso(message, sender_id, loja_id, conversa, texto_id='cardapio5')


def passo_confirma_mesa(message, sender_id, loja_id):
    bot = get_mensagem('mesa5', arg1=message)
    send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_sim_nao())


def passo_pedir_conta(message, sender_id, loja_id, conversa):
    set_variaveis(conversa,
                  itens_pedido=(False, None),
                  datetime_pedido=(False, None))
    if conversa['mesa'] is not None:
        conversa['passo'] = 24
        mensagem_sucesso(sender_id, loja_id, conversa, 'conta')
    else:
        define_sim_nao(conversa, 3, define_passo, 25, define_payload, 'pedir_conta')
        bot = get_mensagem('conta2')
        send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_voltar_menu())


def passo_chamar_garcom(message, sender_id, loja_id, conversa):
    set_variaveis(conversa,
                  itens_pedido=(False, None),
                  datetime_pedido=(False, None))
    if conversa['mesa'] is None:
        define_sim_nao(conversa, 3, define_passo, 22, define_payload, 'chamar_garcom')
        mensagem_mesa(conversa, loja_id, sender_id)
    else:
        conversa['passo'] = 23
        mensagem_sucesso(sender_id, loja_id, conversa, 'garcom')


def passo_pedir_cardapio(message, sender_id, loja_id, conversa):
    set_variaveis(conversa,
                  itens_pedido=(False, None),
                  datetime_pedido=(False, None))
    passo_cardapio(message, sender_id, loja_id, conversa)


def mensagem_sucesso(sender_id, loja_id, conversa, mensagem):
    notificacao_dashboard.apply_async((sender_id, loja_id, conversa, mensagem))
    bot = get_mensagem(mensagem)
    chain(send_text_message.si(sender_id, loja_id, bot), send_generic_message.si(sender_id, loja_id,
                                                                                 get_elements_menu(conversa)))()


def passo_mesa_dependencia(message, sender_id, loja_id, conversa, mensagem, passo):
    conversa['passo'] = passo
    define_mesa(conversa['aux'], conversa)
    conversa['aux'] = None
    set_variaveis(conversa,
                  itens_pedido=(False, None),
                  datetime_pedido=(False, None))
    mensagem_sucesso(sender_id, loja_id, conversa, mensagem)


def passo_finalizar_enviar(message, sender_id, loja_id, conversa):
    if pre_requisito_pedido(sender_id, loja_id, conversa):
        enviar_pedido.delay(sender_id, loja_id, conversa)
        set_variaveis(conversa)
        chain(send_text_message.si(sender_id, loja_id, get_mensagem('enviar')),
              send_generic_message.si(sender_id, loja_id, get_elements_menu(conversa)))()


def passo_finalizar_pedido(message, sender_id, loja_id, conversa):
    if pre_requisito_pedido(sender_id, loja_id, conversa):
        if len(conversa['itens_pedido']) > 0:
            pedidos = None
            for i, item in enumerate(conversa['itens_pedido']):
                if pedidos:
                    pedidos += '\n'
                else:
                    pedidos = ''
                pedidos += repr(item['quantidade']) + ' ' + item['descricao']
            bot1 = pedidos
            bot2 = get_mensagem('finalizar')
            chain(send_text_message.si(sender_id, loja_id, bot1),
                  send_quickreply_message.si(sender_id, loja_id, bot2, get_quickreply_finalizar_pedido(), icon=None))()
        else:
            bot = get_mensagem('rever2')
            chain(send_text_message.si(sender_id, loja_id, bot), send_generic_message.si(sender_id, loja_id,
                                                                                         get_elements_menu(conversa)))()


def passo_pedir_mais(message, sender_id, loja_id, conversa):
    if pre_requisito_pedido(sender_id, loja_id, conversa):
        set_variaveis(conversa,
                      itens_pedido=(False, None),
                      datetime_pedido=(False, None))
        bot = get_mensagem('pedido3')
        send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_voltar_menu())


def add_item_pedido_menu(menu, i, item, offset=0):
    if offset == 0:
        descricao_item = item if len(item) <= 80 else item[:77] + '...'
        menu.append(
            {
                'title': descricao_item,
                'subtitle': u'Edite ou remova este item.',
                'buttons': [
                    {
                        'type': 'postback',
                        'title': u'Editar',
                        'payload': 'editar_item_' + repr(i)
                    },
                    {
                        'type': 'postback',
                        'title': u'Remover',
                        'payload': 'remover_item_' + repr(i)
                    }
                ]
            })
    else:
        menu.append(
            {
                'title': u'Mais itens',
                'subtitle': u'Clique aqui para mostrar mais itens.',
                'buttons': [
                    {
                        'type': 'postback',
                        'title': u'Ver mais',
                        'payload': 'vermais_offset_' + repr(offset)
                    }
                ]
            })


def passo_rever_pedido_2(message, sender_id, loja_id, conversa, offset=0, eh_msg_sucesso=False):
    if pre_requisito_pedido(sender_id, loja_id, conversa):
        if len(conversa['itens_pedido']) > 0:
            menu = []
            limit = 10
            for i, item in enumerate(conversa['itens_pedido'][(0+offset):(limit+offset)]):
                add_item_pedido_menu(menu, (i+offset), repr(item['quantidade']) + ' ' + item['descricao'],
                                     offset=0 if (i/(limit-1) == 0) or len(conversa['itens_pedido']) == (limit+offset)
                                     else ((limit-1)+offset))
            set_variaveis(conversa,
                          itens_pedido=(False, None),
                          datetime_pedido=(False, None))
            if eh_msg_sucesso:
                bot = u'Alteração realizada com sucesso.'
            else:
                bot = 'Clique abaixo para voltar.'
            chain(send_generic_message.si(sender_id, loja_id, menu),
                  send_quickreply_message.si(sender_id, loja_id, bot, get_quickreply_voltar_menu()))()
        else:
            bot = get_mensagem('rever2')
            chain(send_text_message.si(sender_id, loja_id, bot),
                  send_generic_message.si(sender_id, loja_id, get_elements_menu(conversa)))()


def passo_trocar_mesa_2(message, sender_id, loja_id, conversa):
    set_variaveis(conversa,
                  itens_pedido=(False, None),
                  datetime_pedido=(False, None))
    mensagem_mesa(conversa, loja_id, sender_id)


def passo_novo_pedido(message, sender_id, loja_id, conversa):
    if not existe_pedido_andamento(sender_id, loja_id, conversa):
        set_variaveis(conversa, datetime_pedido=(True, datetime.datetime.utcnow()))
        if conversa['mesa'] is None:
            define_sim_nao(conversa, 3, define_passo, 13, define_payload, 'menu_novo_pedido')
            mensagem_mesa(conversa, loja_id, sender_id)
        else:
            conversa['passo'] = 14
            mensagem_pedido(sender_id, loja_id, conversa)


def mensagem_mesa(conversa, loja_id, sender_id):
    bot = get_mensagem('mesa')
    send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_voltar_menu())


def passo_nao_entendido(message, sender_id, loja_id, conversa):
    bot = get_mensagem('robo')
    chain(send_text_message.si(sender_id, loja_id, bot), send_generic_message.si(sender_id, loja_id,
                                                                                 get_elements_menu(conversa)))()


def passo_agradecimento(message, sender_id, loja_id, conversa):
    bot = get_mensagem('agradeco')
    chain(send_text_message.si(sender_id, loja_id, bot), send_generic_message.si(sender_id, loja_id,
                                                                                 get_elements_menu(conversa)))()


def passo_tres(message, sender_id, loja_id, conversa):
    if pre_requisito_pedido(sender_id, loja_id, conversa):
        conversa['nao_entendidas'] += 1
        bot = get_mensagem('anotado2')
        send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_pedido())


def passo_dois(message, sender_id, loja_id, conversa):
    if pre_requisito_pedido(sender_id, loja_id, conversa):
        anota_pedido(message, conversa)
        conversa['passo'] = 8
        set_variaveis(conversa,
                      itens_pedido=(False, None),
                      datetime_pedido=(False, None))
        bot = get_mensagem('anotado', arg1=conversa['usuario']['first_name'])
        send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_pedido())


def passo_um(message, sender_id, loja_id, conversa):
    # send_image_message(sender_id, loja_id, 'cardapio01.jpg', 'image/jpeg')
    if pre_requisito_pedido(sender_id, loja_id, conversa):
        define_mesa(conversa['aux'], conversa)
        conversa['aux'] = None
        conversa['passo'] = 6
        set_variaveis(conversa,
                      itens_pedido=(False, None),
                      datetime_pedido=(False, None))
        mensagem_pedido(sender_id, loja_id, conversa)


def mensagem_pedido(sender_id, loja_id, conversa):
    bot = get_mensagem('pedido')
    bot1 = get_mensagem('pedido1')
    chain(send_text_message.si(sender_id, loja_id, bot),
          send_quickreply_message.si(sender_id, loja_id, bot1, get_quickreply_voltar_menu(), icon=None))()


def passo_trocar_mesa(message, sender_id, loja_id, conversa):
    define_mesa(conversa['aux'], conversa)
    conversa['aux'] = None
    if len(conversa['mesa']) == 2 and conversa['mesa'][0] == conversa['mesa'][1]:
        bot = get_mensagem('mesa4')
        chain(send_text_message.si(sender_id, loja_id, bot),
              send_generic_message.si(sender_id, loja_id, get_elements_menu(conversa)))()
        return
    troca_mesa_dashboard.delay(sender_id, loja_id, conversa)
    set_variaveis(conversa,
                  itens_pedido=(False, None),
                  datetime_pedido=(False, None))
    bot = get_mensagem('mesa3', arg1=conversa['mesa'][0])
    chain(send_text_message.si(sender_id, loja_id, bot),
          send_generic_message.si(sender_id, loja_id, get_elements_menu(conversa)))()


def passo_menu(message, sender_id, loja_id, conversa):
    send_generic_message.delay(sender_id, loja_id, get_elements_menu(conversa))


def passo_ola(message, sender_id, loja_id, conversa):
    bot1 = get_mensagem('ola', arg1=conversa['usuario']['first_name'])
    chain(send_text_message.si(sender_id, loja_id, bot1),
          send_generic_message.si(sender_id, loja_id, get_elements_menu(conversa)))()


if __name__ == "__main__":
    context = ('fullchain.pem', 'privkey.pem')
    flask_app.run(host='0.0.0.0', port=5002, ssl_context=context, threaded=True, debug=True)
