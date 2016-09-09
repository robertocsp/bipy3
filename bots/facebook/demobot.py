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
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from contextlib import contextmanager

try:
    from urllib.parse import parse_qs, urlencode
except ImportError:
    from urlparse import parse_qs
    from urllib import urlencode


logging_handler = RotatingFileHandler(filename='demoindoorbot.log', maxBytes=3*1024*1024, backupCount=2)
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
with open(os.path.join(os.path.join(BASE_DIR, 'bipy3_conf'), 'keys.txt')) as keys_file:
    for line in keys_file:
        key_value_pair = line.strip().split('=')
        if key_value_pair[0] == 'super_user_user':
            SUPER_USER_USER = key_value_pair[1]
        if key_value_pair[0] == 'super_user_password':
            SUPER_USER_PASSWORD = key_value_pair[1]
FACEBOOK_TOKENS = {}
with open(os.path.join(os.path.join(BASE_DIR, 'bipy3_conf'), 'facebook_tokens.txt')) as keys_file:
    for line in keys_file:
        key_value_pair = line.strip().split('=')
        app_log.debug('======>>>>> facebook config ' + key_value_pair[0])
        FACEBOOK_TOKENS[key_value_pair[0]] = key_value_pair[1]

saudacao = ['ola', 'oi', 'bom dia', 'boa tarde', 'boa noite']
agradecimentos = ['obrigado', 'obrigada', 'valeu', 'vlw', 'flw']
EXPIRACAO_CACHE_CONVERSA = 60 * 60 * 2  # 2 horas
SEM_NOME = ''  # TODO se der algum problema no facebook que "nome" usar
ROBOT_ICON = u'\U0001f4bb'


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

    args["access_token"] = FACEBOOK_TOKENS[loja_id]

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


@celery_app.task(time_limit=7)
def send_text_message(sender_id, loja_id, text, icon=ROBOT_ICON):
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


@celery_app.task(time_limit=7)
def send_quickreply_message(sender_id, loja_id, text, quick_replies, icon=ROBOT_ICON):
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


def get_quickreply_menu(conversa):
    menu = []
    possui_itens_pedido = (len(conversa['itens_pedido']) > 0)
    mesa_definida = (conversa['mesa'] is not None)
    pedido_andamento = (conversa['datahora_inicio_pedido'] is not None)
    '''
    menu.append(
        {
            'content_type': 'text',
            'title': u'Ajuda',
            'payload': 'menu_ajuda'
        })
    '''
    menu.append(
        {
            'content_type': 'text',
            'title': u'Novo pedido',
            'payload': 'menu_novo_pedido'
        })
    menu.append(
        {
            'content_type': 'text',
            'title': u'Trocar mesa',
            'payload': 'menu_trocar_mesa'
        })
    if possui_itens_pedido and mesa_definida and pedido_andamento:
        menu.append(
            {
                'content_type': 'text',
                'title': u'Enviar pedido',
                'payload': 'finalizar_pedido'
            })
        menu.append(
            {
                'content_type': 'text',
                'title': u'Rever pedido',
                'payload': 'menu_rever_pedido'
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
                'title': u'Cancelar pedido',
                'payload': 'menu_cancelar_pedido'
            })
    menu.append(
        {
            'content_type': 'text',
            'title': u'Nada por enquanto',
            'payload': 'menu_nada_fazer'
        })
    '''
    menu.append(
        {
            'content_type': 'text',
            'title': u'Fechar a conta',
            'payload': 'menu_fechar_conta'
        })
    '''
    return menu


def get_quickreply_pedido():
    return [
        {
            'content_type': 'text',
            'title': u'Pedir mais coisas',
            'payload': 'pedir_mais'
        },
        {
            'content_type': 'text',
            'title': u'Enviar pedido',
            'payload': 'finalizar_pedido'
        }
    ]


def get_quickreply_finalizar_pedido():
    return [
        {
            'content_type': 'text',
            'title': u'Enviar',
            'payload': 'finalizar_enviar'
        },
        {
            'content_type': 'text',
            'title': u'Rever',
            'payload': 'menu_rever_pedido'
        }
    ]


def get_buttons_forma_pgto():
    return [
        {
            'type':'postback',
            'title':'Dinheiro',
            'payload':'1'
        },
        {
            'type': 'postback',
            'title': u'Crédito',
            'payload': '2'
        },
        {
            'type': 'postback',
            'title': u'Débito',
            'payload': '3'
        },
        {
            'type': 'postback',
            'title': u'Ticket refeição',
            'payload': '4'
        }
    ]


def get_mensagem(id_mensagem, **args):
    mensagens = {
        'ola':        Template(u'Olá, $arg1, me chamo Marvin tudo bem?'),
        'menu':       Template(u'Digite a palavra menu para saber em como posso ajudá-lo(a). '
                               u'Você poderá digitá-la novamente a qualquer momento.'),
        'mesa':       Template(u'Por favor, digite o número de sua mesa para iniciarmos seu atendimento.'),
        'encerrar':   Template(u'Perfeito, caso queira me pedir algo é só digitar menu e escolher a opção '
                               u'"Novo pedido".'),
        'pedido':     Template(u'Excelente, veja o nosso cardápio e digite aqui o que deseja.'),
        # 'pedido1':    Template(u'Pode pedir quantos produtos quiser, colocando-os um por linha OU separando-os com
        # uum ; (ponto e vírgula). Ah, quanto mais detalhado o texto melhor. ;)'),
        'pedido1':    Template(u'Ah, quanto mais detalhado o texto melhor. ;)'),
        'pedido2':    Template(u'Veja um exemplo: 1 água com gelo sem limão'),

        'mesa1':      Template(u'Mil desculpas, mas não consegui identificar o número da sua mesa. Por favor, você '
                               u'poderia digitar novamente o número da sua mesa, só que desta vez utilizando somente '
                               u'números.'),
        'anotado':    Template(u'Anotado.\n$arg1, deseja mais alguma coisa ou posso enviar seu pedido?'),
        'qtde':       Template(u'$arg1\nPerdoe-me, mas não consegui identificar a quantidade do(s) seguinte(s) '
                               u'item(ns) acima.'),
        'qtde1':      Template(u'Peço, por favor, que reenvie sua última mensagem corrigindo-os.'),
        'enviar':     Template(u'Ok, seu pedido já já estará aí.\nCaso queira mais alguma coisa digite menu e escolha '
                               u'a opção "Novo pedido".'),
        'agradeco':   Template(u'Eu que agradeço.\nQualquer coisa é só digitar menu e escolher a opção "Novo pedido".'),
        'robo':       Template(u'Desculpe por não entender, afinal, sou um robô. :)\nVocê gostaria de? '
                               u'Escolha uma das opções abaixo.'),
        'anotado1':   Template(u'Por favor, escolha uma das opções que lhe apresento abaixo.'),
        'mesa2':      Template(u'Por favor, digite o número de sua mesa.'),
        'mesa3':      Template(u'Legal, providenciarei que seus pedidos sejam enviados para sua nova mesa $arg1.'),
        'pedido3':    Template(u'Por favor, pode falar, ou melhor, digitar. :)'),
        'rever':      Template(u'Digite o número entre parênteses seguido da nova quantidade e descrição para editar o '
                               u'item. Por exemplo: 1 2 águas sem gelo'),
        'rever1':     Template(u'Desculpe, mas não consegui editar o item do seu pedido, coloque o número entre '
                               u'parênteses seguido da quantidade e descrição. Exemplo:\n$arg1 $arg2 $arg3'),
        'rever2':     Template(u'Não foram encontrados pedidos em aberto. Como posso auxiliá-lo(a)?'),
        'auxilio':    Template(u'Em que posso ajudá-lo(a)?'),
        'auxilio1':   Template(u'Em que posso ajudá-lo(a) agora?'),
        'dashboard':  Template(u'$arg1, vou dar uma pausa em nossa conversa, pois tem uma mensagem lá de dentro para '
                               u'você. Para finalizar este contato digite menu e escolha a opção "Finalizar contato".'),
        'desenv':     Template(u'Função em desenvolvimento...'),
        'finalizar':  Template(u'Segue, acima, seu pedido para conferência. Confirma o envio?'),
        'dashboard2': Template(u'Contato finalizado. Irei retomar de onde paramos.'),
    }
    return mensagens[id_mensagem].substitute(args)


def define_mesa(message, conversa):
    mesa = [int(s) for s in message.split(' ', 0) if s.isdigit()]
    if len(mesa) == 1:
        conversa['nao_entendidas'] = 0
        conversa['mesa'] = mesa[0]
        return True
    else:
        conversa['nao_entendidas'] += 1
        return False


def anota_pedido(message, conversa):
    erros = []
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
    app_log.debug('=========================>>>>> 3 ' + repr(conversa['itens_pedido']))
    conversa['itens_pedido'] += pedido
    app_log.debug('=========================>>>>> 4 ' + repr(conversa['itens_pedido']))
    return True if len(erros) == 0 else '\n'.join(erros)


def editar_pedido(message, conversa):
    item_pedido = message.strip().split(' ', 2)
    if len(item_pedido) != 2 and len(item_pedido) != 3:
        return False
    i = [int(qtde) for qtde in [item_pedido[0]] if qtde.isdigit()]
    quantidade = [int(qtde) for qtde in [item_pedido[1]] if qtde.isdigit()]
    if len(i) != 1 or len(quantidade) != 1:
        return False
    if quantidade[0] > 0:
        if len(item_pedido) == 3:
            conversa['itens_pedido'][i[0] - 1]['descricao'] = item_pedido[2]
        conversa['itens_pedido'][i[0] - 1]['quantidade'] = quantidade[0]
    else:
        del conversa['itens_pedido'][i[0] - 1]
    return True


def enviar_pedido(sender_id, loja_id, conversa):
    data = {}
    pass
    data['id_loja'] = loja_id
    data['origem'] = 'fbmessenger'
    data['id_cliente'] = sender_id
    data['nome_cliente'] = conversa['usuario']['first_name'] + ' ' + conversa['usuario']['last_name'] \
        if conversa['usuario'] is not None else SEM_NOME
    if conversa['usuario'] is not None:
        data['foto_cliente'] = conversa['usuario']['profile_pic']
    data['mensagem'] = conversa['conversa']
    data['itens_pedido'] = conversa['itens_pedido']
    data['mesa'] = conversa['mesa']
    url = 'http://localhost:8888/bipy3/api/rest/pedido'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(SUPER_USER_USER + ':' + SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    app_log.debug(repr(response))


def resposta_dashboard(message=None, sender_id=None, loja_id=None, conversa=None):
    if unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() == u'menu':
        passo_finalizar_contato(sender_id, loja_id, conversa)
    else:
        data = {}
        pass
        data['id_loja'] = loja_id
        data['origem'] = 'chat'
        data['nome_cliente'] = conversa['usuario']['first_name'] + ' ' + conversa['usuario']['last_name'] \
            if conversa['usuario'] is not None else SEM_NOME
        if conversa['usuario'] is not None:
            data['foto_cliente'] = conversa['usuario']['profile_pic']
        data['cliente'] = message
        data['uid'] = conversa['uid']
        url = 'http://localhost:8888/bipy3/api/rest/mensagem_bot'
        headers = {'content-type': 'application/json',
                   'Authorization': 'Basic ' + base64.b64encode(SUPER_USER_USER + ':' + SUPER_USER_PASSWORD)}
        response = requests.post(url, data=json.dumps(data), headers=headers)
        app_log.debug(repr(response))


def troca_mesa_dashboard(sender_id, loja_id, conversa):
    data = {}
    pass
    data['id_loja'] = loja_id
    data['id_cliente'] = sender_id
    data['mesa'] = conversa['mesa']
    url = 'http://localhost:8888/bipy3/api/rest/troca_mesa'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(SUPER_USER_USER + ':' + SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    app_log.debug(repr(response))


def set_variaveis(conversa, nao_entendidas=(True, 0), itens_pedido=(True, None),
                  datetime_pedido=(True, None), conversa_conversa=(True, None)):
    if datetime_pedido[0]:
        conversa['datahora_inicio_pedido'] = datetime_pedido[1]
    if nao_entendidas[0]:
        conversa['nao_entendidas'] = nao_entendidas[1]
    if itens_pedido[0]:
        conversa['itens_pedido'] = [] if not itens_pedido[1] else itens_pedido[1]
    if conversa_conversa[0]:
        conversa['conversa'] = [] if not conversa_conversa[1] else conversa_conversa[1]


@flask_app.route('/', defaults={'path': ''})
@flask_app.route('/.well-known/acme-challenge/<path:path>')
def ping(path):
    return send_from_directory('.well-known/acme-challenge', path, as_attachment=False,
                               mimetype='text/plain')


@celery_app.task(time_limit=1)
def teste_tarefa():
    while 1:
        app_log.debug('teste_var tarefa:: ' + repr(cache.get('var')))
        app_log.debug('teste_var2 tarefa:: ' + repr(cache.get('var2')))
        time.sleep(4)
        app_log.debug('teste_var2 tarefa:: acordei!!!')
        cache.set('var', cache.get('var') + 1)
        var2 = cache.get('var2')
        if var2 is None:
            app_log.debug('var2 is none:: ')
        if cache.get('var') > 10:
            break


@flask_app.route("/teste_tarefa", methods=['GET', 'POST'])
def teste_tarefa_route():
    uid = request.args.get('uid')
    uid = '1'
    cache.set('var', 0)  # timeout em segundos, sem timeout nunca expira
    cache.add('var2', {
        'itens_pedido': [],
    }, time=10)
    try:
        r = teste_tarefa.delay()
        r.get()
    except TimeLimitExceeded:
        app_log.debug('teste_var2 rota :: nao vai acordar, deu ruim')

    with sender_lock(uid) as lock:
        if lock:
            conversa = cache.get('var2')
            app_log.debug('teste_var2 rota 1:: ' + uid + ':: ' + repr(conversa))
            if uid == '2':
                conversa = None
            conversa['itens_pedido'] += [uid]
            app_log.debug('teste_var2 rota 2:: ' + uid + ':: ' + repr(conversa))
            cache.set('var2', conversa, time=10)
            conversa = cache.get('var2')
            app_log.debug('teste_var2 rota 3:: ' + uid + ':: ' + repr(conversa))
    resp = Response('success', status=200, mimetype='text/plain')
    resp.status_code = 200
    return resp


@contextmanager
def sender_lock(sender_id):
    app_log.debug('lock acquire:: ' + sender_id)
    lock = cache.add(sender_id + 'lock', True, time=10)  # tempo de vida do lock é de 10 segundos, no caso de um erro.
    app_log.debug('lock:: ' + repr(lock) + ' :: ' + sender_id)
    yield lock
    if lock:
        cache.delete(sender_id + 'lock')
        app_log.debug('lock released:: ' + sender_id)
    else:
        app_log.debug('no lock ' + sender_id)


@flask_app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == 'verificacao-muita-segura-do-demo-indoor-bot':
                return request.args.get("hub.challenge")
        return
    if request.method == 'POST':
        app_log.debug(u'INICIO POST :: ')
        output = request.json
        app_log.debug(output)
        event = output['entry'][0]['messaging']
        for x in event:
            sender_id = None
            loja_id = None
            if x.get('sender') and x['sender']['id'] and x.get('recipient') and x['recipient']['id']:
                sender_id = str(x['sender']['id'])
                loja_id = str(x['recipient']['id'])
                app_log.debug('sender_id:: ' + sender_id)
                app_log.debug('loja_id:: ' + loja_id)
            if sender_id is None or loja_id is None:
                pass
            else:
                with sender_lock(sender_id) as lock:
                    if lock:
                        app_log.debug('lock acquired:: ' + sender_id)
                        conversa = cache.get(sender_id)
                        app_log.debug('alguma conversa no cache:: ' + repr(conversa))
                        if conversa is not None:
                            if conversa['usuario'] is None:
                                conversa['usuario'] = pega_usuario(sender_id)
                            cache.set(sender_id, conversa, time=EXPIRACAO_CACHE_CONVERSA)
                            app_log.debug('conversa:: ' + repr(conversa))
                        else:
                            user = pega_usuario(sender_id, loja_id)
                            conversa = {
                                'passo': 0,
                                'usuario': user,
                                'mesa': None,
                                'itens_pedido': [],
                                'conversa': [],
                                'nao_entendidas': 0,
                                'datahora_inicio_pedido': None,
                                'suspensa': 0,
                                'uid': None
                            }
                            app_log.debug('usuario:: ' + repr(user))

                        if x.get('message'):
                            if x['message'].get('text') and not x['message'].get('quick_reply'):
                                message = x['message']['text'].strip()
                                app_log.debug('message: '+message)
                                if conversa['suspensa'] > 0:
                                    resposta_dashboard(message=message, sender_id=sender_id, loja_id=loja_id,
                                                       conversa=conversa)
                                elif unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() \
                                        in saudacao:
                                    conversa['passo'] = 0
                                    passo_ola(message, sender_id, loja_id, conversa)
                                elif u'menu' in unicodedata.normalize('NFKD', message)\
                                        .encode('ASCII', 'ignore').lower():
                                    conversa['passo'] = 1
                                    passo_menu(message, sender_id, loja_id, conversa)
                                elif u'novo pedido' in unicodedata.normalize('NFKD', message)\
                                        .encode('ASCII', 'ignore').lower():
                                    # passos 13 e 14 definidos dentro do método
                                    passo_novo_pedido(message, sender_id, loja_id, conversa)
                                elif conversa['passo'] == 3 or \
                                        conversa['passo'] == 15:
                                    # passos 2 e 3 definidos dentro do método
                                    passo_trocar_mesa(message, sender_id, loja_id, conversa)
                                elif conversa['passo'] == 4 or \
                                        conversa['passo'] == 16:
                                    # passos 4 e 5 definidos dentro do método
                                    passo_rever_pedido(message, sender_id, loja_id, conversa)
                                elif conversa['passo'] == 7 or conversa['passo'] == 13:
                                    # passos 6 e 7 definidos dentro do método
                                    passo_um(message, sender_id, loja_id, conversa)
                                elif conversa['passo'] == 6 or conversa['passo'] == 9 or \
                                        conversa['passo'] == 14 or \
                                        conversa['passo'] == 17:
                                    # passos 8 e 9 definidos dentro do método
                                    passo_dois(message, sender_id, loja_id, conversa)
                                elif conversa['passo'] == 8:
                                    conversa['passo'] = 10
                                    passo_tres(message, sender_id, loja_id, conversa)
                                elif unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower()\
                                        in agradecimentos:
                                    conversa['passo'] = 11
                                    passo_agradecimento(message, sender_id, loja_id, conversa)
                                else:
                                    conversa['passo'] = 12
                                    passo_nao_entendido(message, sender_id, loja_id, conversa)
                            elif x['message'].get('quick_reply') and x['message']['quick_reply'].get('payload'):
                                payload = x['message']['quick_reply']['payload']
                                message = x['message']['text']
                                app_log.debug(payload)
                                if conversa['suspensa'] > 0:
                                    resposta_dashboard(message=message, sender_id=sender_id, loja_id=loja_id,
                                                       conversa=conversa)
                                elif payload == 'menu_novo_pedido':
                                    # passos 13 e 14 definidos dentro do método
                                    passo_novo_pedido(message, sender_id, loja_id, conversa)
                                elif payload == 'menu_cancelar_pedido':
                                    conversa['passo'] = 0
                                    passo_cancelar_pedido(sender_id, loja_id, conversa)
                                elif payload == 'menu_trocar_mesa':
                                    conversa['passo'] = 15
                                    passo_trocar_mesa_2(message, sender_id, loja_id, conversa)
                                elif payload == 'menu_nada_fazer':
                                    passo_nada_fazer(message, sender_id, loja_id, conversa)
                                elif payload == 'menu_rever_pedido':
                                    conversa['passo'] = 16
                                    passo_rever_pedido_2(message, sender_id, loja_id, conversa)
                                elif payload == 'menu_ajuda' or payload == 'menu_fechar_conta':
                                    try:
                                        r = send_text_message.delay(sender_id, loja_id, get_mensagem('desenv'))
                                        r.get()
                                    except TimeLimitExceeded:
                                        app_log.error(u'ERROR:mensagem_pedido!!! Mais de 7 segundos para ter retorno do'
                                                      u' facebook. TimeLimitExceeded.')
                                elif payload == 'pedir_mais':
                                    conversa['passo'] = 17
                                    passo_pedir_mais(message, sender_id, loja_id, conversa)
                                elif payload == 'finalizar_pedido':
                                    conversa['passo'] = 18
                                    passo_finalizar_pedido(message, sender_id, loja_id, conversa)
                                elif payload == 'finalizar_enviar':
                                    conversa['passo'] = 0
                                    passo_finalizar_enviar(message, sender_id, loja_id, conversa)
                                elif payload == 'menu_finalizar_contato':
                                    passo_finalizar_contato(sender_id, loja_id, conversa)
                        elif x.get('dashboard'):
                            conversa['suspensa'] += 1
                            conversa['uid'] = x['dashboard']['uid']
                            try:
                                r = send_text_message.delay(sender_id, loja_id, x['dashboard']['message'],
                                                            icon=u'\U0001f464')
                                r.get()
                            except TimeLimitExceeded:
                                app_log.error(u'ERROR:mensagem dashboard!!! Mais de 7 segundos para ter retorno do'
                                              u' facebook. TimeLimitExceeded.')
                        cache.set(sender_id, conversa, time=EXPIRACAO_CACHE_CONVERSA)
        resp = Response('success', status=200, mimetype='text/plain')
        resp.status_code = 200
        return resp


def pega_usuario(sender_id, loja_id):
    retries = 0
    while retries < 1:
        try:
            app_log.debug('pega_usuario 1:: ')
            user = get_object.delay(sender_id, loja_id)
            app_log.debug('pega_usuario 2:: ')
            user = user.get()
            app_log.debug('pega_usuario 3:: ')
            break
        except SoftTimeLimitExceeded:
            app_log.debug('pega_usuario 4:: ')
            retries += 1
            user = None
            continue
        except Exception as e:
            retries += 1
            app_log.debug('pega_usuario 6:: '+repr(e))
    app_log.debug('pega_usuario 5:: ')
    return user


def passo_finalizar_contato(sender_id, loja_id, conversa):
    if conversa['passo'] == 0 or conversa['passo'] == 1 or \
            conversa['passo'] == 2 or conversa['passo'] == 5:
        passo_menu(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 3 or \
            conversa['passo'] == 15:
        passo_trocar_mesa_2(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 4 or \
            conversa['passo'] == 16:
        passo_rever_pedido_2(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 7 or conversa['passo'] == 13:
        passo_novo_pedido(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 6 or conversa['passo'] == 9 or \
            conversa['passo'] == 14 or conversa['passo'] == 17:
        mensagem_pedido(sender_id, loja_id, conversa)
    elif conversa['passo'] == 8:
        bot = get_mensagem('anotado', arg1=conversa['usuario']['first_name'])
        try:
            r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_pedido())
            r.get()
        except TimeLimitExceeded:
            app_log.error(u'ERROR:quick reply pedido!!! Mais de 7 segundos para ter retorno do'
                          u' facebook. TimeLimitExceeded.')
        conversa['conversa'].append({'bot': bot})
    elif conversa['passo'] == 10:
        passo_tres(None, sender_id, loja_id, conversa)
    elif conversa['passo'] == 18:
        passo_finalizar_pedido(None, sender_id, loja_id, conversa)
    conversa['suspensa'] = 0


def passo_finalizar_enviar(message, sender_id, loja_id, conversa):
    conversa['conversa'].append({'cliente': message})
    enviar_pedido(sender_id, loja_id, conversa)
    set_variaveis(conversa)
    try:
        r = send_text_message.delay(sender_id, loja_id, get_mensagem('enviar'))
        r.get()
    except TimeLimitExceeded:
        app_log.error(u'ERROR:passo_finalizar_enviar!!! Mais de 7 segundos para ter retorno do'
                      u' facebook. TimeLimitExceeded.')


def passo_finalizar_pedido(message, sender_id, loja_id, conversa):
    if message:
        conversa['conversa'].append({'cliente': message})
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
        try:
            r = chain(send_text_message.si(sender_id, loja_id, bot1),
                      send_quickreply_message.si(sender_id, loja_id, bot2, get_quickreply_finalizar_pedido(),
                                                 icon=None))()
            r.get()
            conversa['conversa'].append({'bot': bot1})
            conversa['conversa'].append({'bot': bot2})
        except TimeLimitExceeded:
            app_log.error(u'ERROR:passo_finalizar_pedido!!! Mais de 7 segundos para ter retorno do'
                          u' facebook. TimeLimitExceeded.')
    else:
        bot = get_mensagem('rever2')
        try:
            r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_menu(conversa))
            r.get()
            conversa['conversa'].append({'bot': bot})
        except TimeLimitExceeded:
            app_log.error(u'ERROR:passo_finalizar_pedido!!! Mais de 7 segundos para ter retorno do'
                          u' facebook. TimeLimitExceeded.')


def passo_pedir_mais(message, sender_id, loja_id, conversa):
    conversa['conversa'].append({'cliente': message})
    set_variaveis(conversa,
                  itens_pedido=(False, None),
                  datetime_pedido=(False, None),
                  conversa_conversa=(False, None))
    bot = get_mensagem('pedido3')
    try:
        r = send_text_message.delay(sender_id, loja_id, bot)
        r.get()
        conversa['conversa'].append({'bot': bot})
    except TimeLimitExceeded:
        app_log.error(u'ERROR:passo_pedir_mais!!! Mais de 7 segundos para ter retorno do'
                      u' facebook. TimeLimitExceeded.')


def passo_rever_pedido_2(message, sender_id, loja_id, conversa):
    if message:
        conversa['conversa'].append({'cliente': message})
    if len(conversa['itens_pedido']) > 0:
        pedidos = None
        for i, item in enumerate(conversa['itens_pedido']):
            if pedidos:
                pedidos += '\n'
            else:
                pedidos = ''
            pedidos += '(' + repr(i + 1) + '): ' + repr(item['quantidade']) + ' ' + item['descricao']
        set_variaveis(conversa,
                      itens_pedido=(False, None),
                      datetime_pedido=(False, None),
                      conversa_conversa=(False, None))
        bot1 = get_mensagem('rever')
        bot2 = pedidos
        try:
            r = chain(send_text_message.si(sender_id, loja_id, bot1),
                      send_text_message.si(sender_id, loja_id, bot2, icon=None))()
            r.get()
            conversa['conversa'].append({'bot': bot1})
            conversa['conversa'].append({'bot': bot2})
        except TimeLimitExceeded:
            app_log.error(u'ERROR:passo_rever_pedido_2!!! Mais de 7 segundos para ter retorno do'
                          u' facebook. TimeLimitExceeded.')
    else:
        bot = get_mensagem('rever2')
        try:
            r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_menu(conversa))
            r.get()
            conversa['conversa'].append({'bot': bot})
            # TODO ?pegar os pedidos em aberto do servidor? pode ser complicado, pois o pedido já pode ter ido, é melhor
            # TODO deixar isso manualmente.
        except TimeLimitExceeded:
            app_log.error(u'ERROR:passo_rever_pedido_2!!! Mais de 7 segundos para ter retorno do'
                          u' facebook. TimeLimitExceeded.')


def passo_nada_fazer(message, sender_id, loja_id, conversa):
    conversa['conversa'].append({'cliente': message})
    set_variaveis(conversa,
                  itens_pedido=(False, None),
                  datetime_pedido=(False, None),
                  conversa_conversa=(False, None))
    bot = get_mensagem('encerrar')
    try:
        r = send_text_message.delay(sender_id, loja_id, bot)
        r.get()
        conversa['conversa'].append({'bot': bot})
    except TimeLimitExceeded:
        app_log.error(u'ERROR:passo_nada_fazer!!! Mais de 7 segundos para ter retorno do'
                      u' facebook. TimeLimitExceeded.')


def passo_trocar_mesa_2(message, sender_id, loja_id, conversa):
    if message:
        conversa['conversa'].append({'cliente': message})
    set_variaveis(conversa,
                  itens_pedido=(False, None),
                  datetime_pedido=(False, None),
                  conversa_conversa=(False, None))
    bot = get_mensagem('mesa2')
    try:
        r = send_text_message.delay(sender_id, loja_id, bot)
        r.get()
        conversa['conversa'].append({'bot': bot})
    except TimeLimitExceeded:
        app_log.error(u'ERROR:passo_trocar_mesa_2!!! Mais de 7 segundos para ter retorno do'
                      u' facebook. TimeLimitExceeded.')


def passo_cancelar_pedido(sender_id, loja_id, conversa):
    set_variaveis(conversa)
    try:
        r = send_text_message.delay(sender_id, loja_id, get_mensagem('encerrar'))
        r.get()
    except TimeLimitExceeded:
        app_log.error(u'ERROR:passo_cancelar_pedido!!! Mais de 7 segundos para ter retorno do'
                      u' facebook. TimeLimitExceeded.')


def passo_novo_pedido(message, sender_id, loja_id, conversa):
    # TODO verificar pedido nao enviado
    # verificar se existe pedido nao enviado para poder perguntar o que o cliente deseja fazer
    # com ele, enviar, cancelar, rever pedido, adicionar mais itens
    # por enquanto, como nao tem esta tratativa o pedido pendente de envio sera cancelado
    set_variaveis(conversa, datetime_pedido=(True, datetime.datetime.utcnow()))
    if message:
        conversa['conversa'].append({'cliente': message})
    if conversa['mesa'] is None:
        conversa['passo'] = 13
        bot = get_mensagem('mesa')
        try:
            r = send_text_message.delay(sender_id, loja_id, bot)
            r.get()
            conversa['conversa'].append({'bot': bot})
        except TimeLimitExceeded:
            app_log.error(u'ERROR:passo_novo_pedido!!! Mais de 7 segundos para ter retorno do'
                          u' facebook. TimeLimitExceeded.')
    else:
        conversa['passo'] = 14
        mensagem_pedido(sender_id, loja_id, conversa)


def passo_nao_entendido(message, sender_id, loja_id, conversa):
    conversa['conversa'].append({'cliente': message})
    bot = get_mensagem('robo')
    try:
        r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_menu(conversa))
        r.get()
        conversa['conversa'].append({'bot': bot})
    except TimeLimitExceeded:
        app_log.error(u'ERROR:passo_nao_entendido!!! Mais de 7 segundos para ter retorno do'
                      u' facebook. TimeLimitExceeded.')


def passo_agradecimento(message, sender_id, loja_id, conversa):
    conversa['conversa'].append({'cliente': message})
    bot = get_mensagem('agradeco')
    try:
        r = send_text_message.delay(sender_id, loja_id, bot)
        r.get()
        conversa['conversa'].append({'bot': bot})
    except TimeLimitExceeded:
        app_log.error(u'ERROR:passo_agradecimento!!! Mais de 7 segundos para ter retorno do'
                      u' facebook. TimeLimitExceeded.')


def passo_tres(message, sender_id, loja_id, conversa):
    if message:
        conversa['conversa'].append({'cliente': message})
    conversa['nao_entendidas'] += 1
    bot = get_mensagem('anotado1')
    try:
        r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_pedido())
        r.get()
        conversa['conversa'].append({'bot': bot})
    except TimeLimitExceeded:
        app_log.error(u'ERROR:passo_tres!!! Mais de 7 segundos para ter retorno do'
                      u' facebook. TimeLimitExceeded.')


def passo_dois(message, sender_id, loja_id, conversa):
    conversa['conversa'].append({'cliente': message})
    is_pedido_anotado = anota_pedido(message, conversa)
    if is_pedido_anotado is True:
        conversa['passo'] = 8
        set_variaveis(conversa,
                      itens_pedido=(False, None),
                      datetime_pedido=(False, None),
                      conversa_conversa=(False, None))
        bot = get_mensagem('anotado', arg1=conversa['usuario']['first_name'])
        try:
            r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_pedido())
            r.get()
            conversa['conversa'].append({'bot': bot})
        except TimeLimitExceeded:
            app_log.error(u'ERROR:passo_dois!!! Mais de 7 segundos para ter retorno do'
                          u' facebook. TimeLimitExceeded.')
    else:
        conversa['passo'] = 9
        conversa['nao_entendidas'] += 1
        if conversa['nao_entendidas'] > 1:
            bot = get_mensagem('robo')
            try:
                r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_menu(conversa))
                r.get()
                conversa['conversa'].append({'bot': bot})
            except TimeLimitExceeded:
                app_log.error(u'ERROR:passo_dois!!! Mais de 7 segundos para ter retorno do'
                              u' facebook. TimeLimitExceeded.')
        else:
            bot1 = get_mensagem('qtde', arg1=is_pedido_anotado)
            bot2 = get_mensagem('qtde1')
            try:
                r = chain(send_text_message.si(sender_id, loja_id, bot1),
                          send_text_message.si(sender_id, loja_id, bot2, icon=None))()
                r.get()
                conversa['conversa'].append({'bot': bot1})
                conversa['conversa'].append({'bot': bot2})
            except TimeLimitExceeded:
                app_log.error(u'ERROR:passo_dois!!! Mais de 7 segundos para ter retorno do'
                              u' facebook. TimeLimitExceeded.')


def passo_um(message, sender_id, loja_id, conversa):
    conversa['conversa'].append({'cliente': message})
    # send_image_message(sender_id, loja_id, 'cardapio01.jpg', 'image/jpeg')
    if define_mesa(message, conversa):
        conversa['passo'] = 6
        set_variaveis(conversa,
                      itens_pedido=(False, None),
                      datetime_pedido=(False, None),
                      conversa_conversa=(False, None))
        mensagem_pedido(sender_id, loja_id, conversa)
    else:
        conversa['passo'] = 7
        if conversa['nao_entendidas'] > 1:
            bot = get_mensagem('robo')
            try:
                r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_menu(conversa))
                r.get()
                conversa['conversa'].append({'bot': bot})
            except TimeLimitExceeded:
                app_log.error(u'ERROR:passo_um!!! Mais de 7 segundos para ter retorno do'
                              u' facebook. TimeLimitExceeded.')
        else:
            bot = get_mensagem('mesa1')
            try:
                r = send_text_message.delay(sender_id, loja_id, bot)
                r.get()
                conversa['conversa'].append({'bot': bot})
            except TimeLimitExceeded:
                app_log.error(u'ERROR:passo_um!!! Mais de 7 segundos para ter retorno do'
                              u' facebook. TimeLimitExceeded.')


def mensagem_pedido(sender_id, loja_id, conversa):
    bot1 = get_mensagem('pedido')
    bot2 = get_mensagem('pedido1')
    bot3 = get_mensagem('pedido2')
    try:
        r = chain(send_text_message.si(sender_id, loja_id, bot1),
                  send_text_message.si(sender_id, loja_id, bot2, icon=None),
                  send_text_message.si(sender_id, loja_id, bot3, icon=None))()
        r.get()
        conversa['conversa'].append({'bot': bot1})
        conversa['conversa'].append({'bot': bot2})
        conversa['conversa'].append({'bot': bot3})
    except TimeLimitExceeded:
        app_log.error(u'ERROR:mensagem_pedido!!! Mais de 7 segundos para ter retorno do facebook. TimeLimitExceeded.')


def passo_rever_pedido(message, sender_id, loja_id, conversa):
    conversa['conversa'].append({'cliente': message})
    if not editar_pedido(message, conversa):
        conversa['passo'] = 4
        conversa['nao_entendidas'] += 1
        if conversa['nao_entendidas'] > 1:
            bot = get_mensagem('robo')
            try:
                r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_menu(conversa))
                r.get()
                conversa['conversa'].append({'bot': bot})
            except TimeLimitExceeded:
                app_log.error(u'ERROR:passo_rever_pedido!!! Mais de 7 segundos para ter retorno do'
                              u' facebook. TimeLimitExceeded.')
        else:
            bot = get_mensagem('rever1', arg1='1',
                               arg2=repr(conversa
                                         ['itens_pedido'][0]['quantidade'] + 2),
                               arg3=conversa['itens_pedido'][0]['descricao'])
            try:
                r = send_text_message.delay(sender_id, loja_id, bot)
                r.get()
                conversa['conversa'].append({'bot': bot})
            except TimeLimitExceeded:
                app_log.error(u'ERROR:passo_rever_pedido!!! Mais de 7 segundos para ter retorno do'
                              u' facebook. TimeLimitExceeded.')
    else:
        conversa['passo'] = 5
        set_variaveis(conversa,
                      itens_pedido=(False, None),
                      datetime_pedido=(False, None),
                      conversa_conversa=(False, None))
        bot = get_mensagem('auxilio1')
        try:
            r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_menu(conversa))
            r.get()
            conversa['conversa'].append({'bot': bot})
        except TimeLimitExceeded:
            app_log.error(u'ERROR:passo_rever_pedido!!! Mais de 7 segundos para ter retorno do'
                          u' facebook. TimeLimitExceeded.')


def passo_trocar_mesa(message, sender_id, loja_id, conversa):
    conversa['conversa'].append({'cliente': message})
    if define_mesa(message, conversa):
        troca_mesa_dashboard(sender_id, loja_id, conversa)
        conversa['passo'] = 2
        set_variaveis(conversa,
                      itens_pedido=(False, None),
                      datetime_pedido=(False, None),
                      conversa_conversa=(False, None))
        bot1 = get_mensagem('mesa3', arg1=conversa['mesa'])
        bot2 = get_mensagem('auxilio1')
        try:
            r = chain(send_text_message.si(sender_id, loja_id, bot1),
                      send_quickreply_message.si(sender_id, loja_id, bot2, get_quickreply_menu(conversa), icon=None))()
            r.get()
            conversa['conversa'].append({'bot': bot1})
            conversa['conversa'].append({'bot': bot2})
        except TimeLimitExceeded:
            app_log.error(u'ERROR:passo_trocar_mesa!!! Mais de 7 segundos para ter retorno do'
                          u' facebook. TimeLimitExceeded.')
    else:
        conversa['passo'] = 3
        if conversa['nao_entendidas'] > 1:
            bot = get_mensagem('robo')
            try:
                r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_menu(conversa))
                r.get()
                conversa['conversa'].append({'bot': bot})
            except TimeLimitExceeded:
                app_log.error(u'ERROR:passo_trocar_mesa!!! Mais de 7 segundos para ter retorno do'
                              u' facebook. TimeLimitExceeded.')
        else:
            bot = get_mensagem('mesa1')
            try:
                r = send_text_message.delay(sender_id, loja_id, bot)
                r.get()
                conversa['conversa'].append({'bot': bot})
            except TimeLimitExceeded:
                app_log.error(u'ERROR:passo_trocar_mesa!!! Mais de 7 segundos para ter retorno do'
                              u' facebook. TimeLimitExceeded.')


def passo_menu(message, sender_id, loja_id, conversa):
    if message:
        conversa['conversa'].append({'cliente': message})
    bot = get_mensagem('auxilio')
    try:
        r = send_quickreply_message.delay(sender_id, loja_id, bot, get_quickreply_menu(conversa))
        r.get()
        conversa['conversa'].append({'bot': bot})
    except TimeLimitExceeded:
        app_log.error(u'ERROR:passo_menu!!! Mais de 7 segundos para ter retorno do'
                      u' facebook. TimeLimitExceeded.')


def passo_ola(message, sender_id, loja_id, conversa):
    conversa['conversa'].append({'cliente': message})
    bot1 = get_mensagem('ola', arg1=conversa['usuario']['first_name'])
    bot2 = get_mensagem('menu')
    try:
        r = chain(send_text_message.si(sender_id, loja_id, bot1),
                  send_text_message.si(sender_id, loja_id, bot2, icon=None))()
        r.get()
        conversa['conversa'].append({'bot': bot1})
        conversa['conversa'].append({'bot': bot2})
    except TimeLimitExceeded:
        app_log.error(u'ERROR:passo_ola!!! Mais de 7 segundos para ter retorno do'
                      u' facebook. TimeLimitExceeded.')


if __name__ == "__main__":
    context = ('fullchain.pem', 'privkey.pem')
    flask_app.run(host='0.0.0.0', port=5002, ssl_context=context, threaded=True, debug=True)
