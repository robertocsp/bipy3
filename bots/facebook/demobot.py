# -*- coding: utf-8 -*-
"""
This bot listens to port 5002 for incoming connections from Facebook. It takes
in any messages that the bot receives and echos it back.
"""
import os
import logging
import requests
import json
import unicodedata
import datetime

from string import Template
from flask import Flask, request, send_from_directory, Response
from logging.handlers import RotatingFileHandler
from logging import Formatter

try:
    from urllib.parse import parse_qs, urlencode
except ImportError:
    from urlparse import parse_qs
    from urllib import urlencode

app = Flask(__name__)
FACEBOOK_GRAPH_URL = "https://graph.facebook.com/v2.7"
TOKEN = "TOKEN"

logging_handler = RotatingFileHandler(filename='demoindoorbot.log', maxBytes=3*1024*1024, backupCount=2)
logging_handler.setFormatter(Formatter(logging.BASIC_FORMAT, None))
app_log = logging.getLogger('root')
app_log.setLevel(logging.DEBUG)
app_log.addHandler(logging_handler)

conversas = {}
agradecimentos = ['obrigado', 'obrigada', 'valeu', 'vlw', 'flw']


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


def get_object(fb_id, **args):
    """Fetches the given object from the graph."""
    return fb_request('/' + fb_id, args=args)


def post(post_args=None, json=None, files=None, headers=None):
    return fb_request('/me/messages', post_args=post_args, json=json, files=files, headers=headers)


def fb_request(path, args=None, post_args=None, json=None, files=None, method=None, headers=None):
    """Fetches the given path in the Graph API.

    We translate args to a valid query string. If post_args is
    given, we send a POST request to the given path with the given
    arguments.

    """

    args = args or {}

    if post_args is not None or json is not None:
        method = "POST"

    args["access_token"] = TOKEN

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


def send_image_message(recipient_id, image_path, content_type):
    '''
        This sends an image to the specified recipient.
        Image must be PNG or JPEG.
        Input:
          recipient_id: recipient id to send to
          image_path: path to image to be sent
        Output:
          Response from API as <dict>
    '''
    payload = {
        'recipient': json.dumps(
            {
                'id': recipient_id
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
    return post(post_args=payload, files=multipart_data)


def send_button_message(recipient_id, text, buttons):
    payload = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': [
                        {
                            'title': text,
                            'buttons': buttons
                        }
                    ]
                }
            }
        }
    }
    return post(json=payload)


def send_text_message(recipient_id, text):
    payload = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'text': text
        }
    }
    return post(json=payload)


def send_quickreply_message(recipient_id, text, quick_replies):
    payload = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'text': text,
            'quick_replies': quick_replies
        }
    }
    return post(json=payload)


def get_quickreply_menu():
    return [
        {
            'content_type': 'text',
            'title': u'Ajuda',
            'payload': 'menu_ajuda'
        },
        {
            'content_type': 'text',
            'title': u'Novo pedido',
            'payload': 'menu_novo_pedido'
        },
        {
            'content_type': 'text',
            'title': u'Trocar mesa',
            'payload': 'menu_trocar_mesa'
        },
        {
            'content_type': 'text',
            'title': u'Enviar pedido',
            'payload': 'finalizar_pedido'
        },
        {
            'content_type': 'text',
            'title': u'Rever pedido',
            'payload': 'menu_rever_pedido'
        },
        {
            'content_type': 'text',
            'title': u'+ itens ao pedido',
            'payload': 'menu_adicionar_item_pedido'
        },
        {
            'content_type': 'text',
            'title': u'Cancelar pedido',
            'payload': 'menu_cancelar_pedido'
        },
        {
            'content_type': 'text',
            'title': u'Nada por enquanto',
            'payload': 'menu_nada_fazer'
        },
        {
            'content_type': 'text',
            'title': u'Fechar a conta',
            'payload': 'menu_fechar_conta'
        }
    ]


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
        'ola':       Template(u'Olá, $arg1, me chamo Marvin tudo bem?'),
        'menu':      Template(u'Digite a palavra menu para saber em como posso ajudá-lo(a). '
                              u'Você poderá digitá-la novamente a qualquer momento.'),
        'mesa':      Template(u'Por favor, digite o número de sua mesa para iniciarmos seu atendimento.'),
        'encerrar':  Template(u'Perfeito, caso queira me pedir algo é só digitar menu e escolher a opção '
                              u'"Novo pedido".'),
        'pedido':    Template(u'Excelente, veja o nosso cardápio e digite aqui o que deseja. Só peço que digite '
                              u'primeiro o número, indicando a quantidade, e depois o texto do seu pedido.'),
        'pedido1':   Template(u'Pode pedir quantos produtos quiser, colocando-os um por linha OU separando-os com um ; '
                              u'(ponto e vírgula). Ah, quanto mais detalhado o texto melhor. ;)'),
        'pedido2':   Template(u'Veja um exemplo: 1 água com gelo sem limão'),

        'mesa1':     Template(u'Mil desculpas, mas não consegui identificar o número da sua mesa. Por favor, você '
                              u'poderia digitar novamente o número da sua mesa, só que desta vez utilizando somente '
                              u'números.'),
        'anotado':   Template(u'Anotado.\n$arg1, deseja mais alguma coisa ou posso enviar seu pedido?'),
        'qtde':      Template(u'$arg1\nPerdoe-me, mas não consegui identificar a quantidade do(s) seguinte(s) item(ns) '
                              u'acima.'),
        'qtde1':     Template(u'Peço, por favor, que reenvie sua última mensagem corrigindo-os.'),
        'enviar':    Template(u'Ok, seu pedido já já estará aí.\nCaso queira mais alguma coisa digitar menu e escolher '
                              u'a opção "Novo pedido".'),
        'agradeco':  Template(u'Eu que agradeço.\nQualquer coisa é só digitar menu e escolher a opção "Novo pedido".'),
        'robo':      Template(u'Desculpe por não entender, afinal, sou um robô. :)\nVocê gostaria de? '
                              u'Escolha uma das opções abaixo.'),
        'anotado1':  Template(u'Por favor, escolha uma das opções que lhe apresento abaixo.'),
        'mesa2':     Template(u'Por favor, digite o número de sua mesa.'),
        'mesa3':     Template(u'Legal, providenciarei que seus pedidos não enviados sejam enviados para sua nova '
                              u'mesa.'),
        'pedido3':   Template(u'Por favor, pode falar, ou melhor, digitar. :)'),
        'rever':     Template(u'Digite o número entre parênteses seguido da nova quantidade e descrição para editar o '
                              u'item. Por exemplo: 1 2 águas sem gelo'),
        'rever1':    Template(u'Desculpe, mas não consegui editar o item do seu pedido, coloque o número entre '
                              u'parênteses seguido da quantidade e descrição. Exemplo:\n$arg1 $arg2 $arg3'),
        'rever2':    Template(u'Não foram encontrados pedidos em aberto. Como posso auxiliá-lo(a)?'),
        'auxilio':   Template(u'Em que posso ajudá-lo(a)?'),
        'auxilio1':  Template(u'Em que posso ajudá-lo(a) agora?'),
        'desenv':    Template(u'Função em desenvolvimento...')
    }
    return mensagens[id_mensagem].substitute(args)


def define_mesa(message, recipient_id):
    mesa = [int(s) for s in message.split() if s.isdigit()]
    if len(mesa) == 1:
        conversas[recipient_id]['nao_entendidas'] = 0
        conversas[recipient_id]['mesa'] = mesa[0]
        return True
    else:
        conversas[recipient_id]['nao_entendidas'] += 1
        if conversas[recipient_id]['nao_entendidas'] > 1:
            result = send_quickreply_message(recipient_id, get_mensagem('robo'),
                                             get_quickreply_menu())
        else:
            result = send_text_message(recipient_id, get_mensagem('mesa1'))
        return False


def anota_pedido(message, recipient_id):
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
            if len(quantidade) == 1:
                pedido.append({
                    'descricao': item_pedido[1],
                    'quantidade': quantidade[0]
                })
            else:
                pedido = []
                if len(item_pedido) == 2:
                    erros.append(item_pedido[1])
                else:
                    erros.append(item_pedido[0])
    app_log.debug('=========================>>>>> 3 ' + repr(conversas[recipient_id]['itens_pedido']))
    conversas[recipient_id]['itens_pedido'] += pedido
    app_log.debug('=========================>>>>> 4 ' + repr(conversas[recipient_id]['itens_pedido']))
    return True if len(erros) == 0 else '\n'.join(erros)


def editar_pedido(message, recipient_id):
    item_pedido = message.strip().split(' ', 2)
    if len(item_pedido) != 3:
        return False
    i = [int(qtde) for qtde in [item_pedido[0]] if qtde.isdigit()]
    quantidade = [int(qtde) for qtde in [item_pedido[1]] if qtde.isdigit()]
    if len(i) != 1 or len(quantidade) != 1:
        return False
    conversas[recipient_id]['itens_pedido'][i[0] - 1]['descricao'] = item_pedido[2]
    conversas[recipient_id]['itens_pedido'][i[0] - 1]['quantidade'] = quantidade[0]
    return True


def set_variaveis(recipient_id, passo=(True, 0), nao_entendidas=(True, 0), itens_pedido=(True, None),
                  menu_acessado=(True, None), datetime_pedido=(True, None)):
    app_log.debug('==set_variaveis=======================>>>>> 1 ' + recipient_id)
    app_log.debug('==set_variaveis=======================>>>>> 2 ' + repr(passo))
    app_log.debug('==set_variaveis=======================>>>>> 3 ' + repr(nao_entendidas))
    app_log.debug('==set_variaveis=======================>>>>> 4 ' + repr(itens_pedido))
    app_log.debug('==set_variaveis=======================>>>>> 5 ' + repr(menu_acessado))
    app_log.debug('==set_variaveis=======================>>>>> 6 ' + repr(datetime_pedido))
    if datetime_pedido[0]:
        conversas[recipient_id]['datahora_inicio_pedido'] = datetime_pedido[1]
    if passo[0]:
        conversas[recipient_id]['passo'] = passo[1]
    if nao_entendidas[0]:
        conversas[recipient_id]['nao_entendidas'] = nao_entendidas[1]
    if itens_pedido[0]:
        conversas[recipient_id]['itens_pedido'] = [] if not itens_pedido[1] else itens_pedido[1]
    if menu_acessado[0]:
        conversas[recipient_id]['menu_acessado'] = menu_acessado[1]
    app_log.debug('==set_variaveis=======================>>>>> 7 ' + repr(conversas[recipient_id]
                                                                          ['datahora_inicio_pedido']))
    app_log.debug('==set_variaveis=======================>>>>> 8 ' + repr(conversas[recipient_id]['passo']))
    app_log.debug('==set_variaveis=======================>>>>> 9 ' + repr(conversas[recipient_id]['nao_entendidas']))
    app_log.debug('==set_variaveis=======================>>>>> 10 ' + repr(conversas[recipient_id]['itens_pedido']))
    app_log.debug('==set_variaveis=======================>>>>> 11 ' + repr(conversas[recipient_id]['menu_acessado']))


@app.route('/', defaults={'path': ''})
@app.route('/.well-known/acme-challenge/<path:path>')
def ping(path):
    return send_from_directory('.well-known/acme-challenge', path, as_attachment=False,
                               mimetype='text/plain')


@app.route("/webhook", methods=['GET', 'POST'])
def hello():
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == 'verificacao-muita-segura-do-demo-indoor-bot':
                return request.args.get("hub.challenge")
        return
    if request.method == 'POST':
        app_log.debug(u'INICIO POST')
        output = request.json
        app_log.debug(output)
        event = output['entry'][0]['messaging']
        for x in event:
            if x.get('sender') and x['sender']['id']:
                recipient_id = str(x['sender']['id'])
                app_log.debug('recipient_id:: ' + recipient_id)
                try:
                    conversas[recipient_id]
                    app_log.debug('conversas:: ' + repr(conversas))
                except KeyError:
                    user = get_object(recipient_id)
                    conversas[recipient_id] = {
                        'passo': 0,
                        'usuario': user,
                        'mesa': -1,
                        'itens_pedido': [],
                        'conversa': [],
                        'nao_entendidas': 0,
                        'datahora_inicio_pedido': None,
                        'menu_acessado': None,
                    }
                    app_log.debug('usuario:: ' + repr(user))

            if x.get('message'):
                if x['message'].get('text') and not x['message'].get('quick_reply'):
                    message = x['message']['text']
                    app_log.debug('message: '+message)

                    if unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() == u'ola':
                        # TODO verificar pedido nao enviado
                        # verificar se existe pedido nao enviado para poder perguntar o que o cliente deseja fazer
                        # com ele, enviar, cancelar, rever pedido, adicionar mais itens
                        # por enquanto, como nao tem esta tratativa o pedido pendente de envio sera cancelado
                        set_variaveis(recipient_id)
                        result = send_text_message(recipient_id, get_mensagem('ola',
                                                                              arg1=conversas[recipient_id]['usuario']
                                                                                            ['first_name']))
                        app_log.debug(result)
                        result = send_text_message(recipient_id, get_mensagem('menu'))
                    elif unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() == u'menu':
                        result = send_quickreply_message(recipient_id, get_mensagem('auxilio'), get_quickreply_menu())
                    elif conversas[recipient_id]['menu_acessado'] == 'menu_trocar_mesa':  # troca de mesa
                        if define_mesa(message, recipient_id):
                            set_variaveis(recipient_id,
                                          passo=(False, None),
                                          itens_pedido=(False, None),
                                          datetime_pedido=(False, None))
                            result = send_text_message(recipient_id, get_mensagem('mesa3'))
                            result = send_quickreply_message(recipient_id, get_mensagem('auxilio1'),
                                                             get_quickreply_menu())
                    elif conversas[recipient_id]['menu_acessado'] == 'menu_rever_pedido':  # rever item do pedido
                        if not editar_pedido(message, recipient_id):
                            conversas[recipient_id]['nao_entendidas'] += 1
                            if conversas[recipient_id]['nao_entendidas'] > 1:
                                result = send_quickreply_message(recipient_id, get_mensagem('robo'),
                                                                 get_quickreply_menu())
                            else:
                                result = send_text_message(recipient_id, get_mensagem('rever1',
                                                                                      arg1='1',
                                                                                      arg2=repr(conversas
                                                                                                [recipient_id]
                                                                                                ['itens_pedido'][0]
                                                                                                ['quantidade']+2),
                                                                                      arg3=conversas[recipient_id]
                                                                                                    ['itens_pedido'][0]
                                                                                                    ['descricao']))
                        else:
                            set_variaveis(recipient_id,
                                          passo=(False, None),
                                          itens_pedido=(False, None),
                                          datetime_pedido=(False, None))
                            result = send_quickreply_message(recipient_id, get_mensagem('auxilio1'),
                                                             get_quickreply_menu())
                    elif conversas[recipient_id]['passo'] == 1:
                        # result = send_image_message(recipient_id, 'cardapio01.jpg', 'image/jpeg')
                        # app_log.debug(result)
                        if define_mesa(message, recipient_id):
                            set_variaveis(recipient_id,
                                          passo=(True, 2),
                                          itens_pedido=(False, None),
                                          datetime_pedido=(False, None))
                            result = send_text_message(recipient_id, get_mensagem('pedido'))
                            result = send_text_message(recipient_id, get_mensagem('pedido1'))
                            result = send_text_message(recipient_id, get_mensagem('pedido2'))
                    elif conversas[recipient_id]['passo'] == 2:
                        is_pedido_anotado = anota_pedido(message, recipient_id)
                        if is_pedido_anotado == True:
                            set_variaveis(recipient_id,
                                          passo=(True, 3),
                                          itens_pedido=(False, None),
                                          datetime_pedido=(False, None))
                            result = send_quickreply_message(recipient_id,
                                                             get_mensagem('anotado',
                                                                          arg1=conversas[recipient_id]
                                                                                        ['usuario']['first_name']),
                                                             get_quickreply_pedido())
                        else:
                            conversas[recipient_id]['nao_entendidas'] += 1
                            if conversas[recipient_id]['nao_entendidas'] > 1:
                                result = send_quickreply_message(recipient_id, get_mensagem('robo'),
                                                                 get_quickreply_menu())
                            else:
                                result = send_text_message(recipient_id, get_mensagem('qtde', arg1=is_pedido_anotado))
                                result = send_text_message(recipient_id, get_mensagem('qtde1'))
                    elif conversas[recipient_id]['passo'] == 3:
                        conversas[recipient_id]['nao_entendidas'] += 1
                        result = send_quickreply_message(recipient_id, get_mensagem('anotado1'),
                                                         get_quickreply_pedido())
                    elif unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() in agradecimentos:
                        result = send_text_message(recipient_id, get_mensagem('agradeco'))
                    else:
                        result = send_quickreply_message(recipient_id, get_mensagem('robo'),
                                                         get_quickreply_menu())
                elif x['message'].get('quick_reply') and x['message']['quick_reply'].get('payload'):
                    payload = x['message']['quick_reply']['payload']
                    app_log.debug(payload)
                    if payload == 'menu_novo_pedido':
                        # TODO verificar pedido nao enviado
                        # verificar se existe pedido nao enviado para poder perguntar o que o cliente deseja fazer
                        # com ele, enviar, cancelar, rever pedido, adicionar mais itens
                        # por enquanto, como nao tem esta tratativa o pedido pendente de envio sera cancelado
                        set_variaveis(recipient_id, datetime_pedido=(True, datetime.datetime.utcnow()))
                        # TODO criar rotina que zera a informacao de mesa do cliente
                        # ideal eh ter uma rotina que zere a informacao de mesa do usuario, alem do fechar conta, para
                        # nao perguntar toda vez o numero da mesa do cliente, quando for iniciar um pedido
                        conversas[recipient_id]['mesa'] = -1
                        if conversas[recipient_id]['mesa'] == -1:
                            conversas[recipient_id]['passo'] = 1
                            result = send_text_message(recipient_id, get_mensagem('mesa'))
                        else:
                            conversas[recipient_id]['passo'] = 2
                            result = send_text_message(recipient_id, get_mensagem('pedido'))
                            result = send_text_message(recipient_id, get_mensagem('pedido1'))
                            result = send_text_message(recipient_id, get_mensagem('pedido2'))
                    elif payload == 'menu_cancelar_pedido':
                        set_variaveis(recipient_id)
                        result = send_text_message(recipient_id, get_mensagem('encerrar'))
                    elif payload == 'menu_trocar_mesa':
                        # TODO enviar para o servidor a troca de mesa para atualizar os pedidos em abeto
                        set_variaveis(recipient_id,
                                      passo=(False, None),
                                      itens_pedido=(False, None),
                                      datetime_pedido=(False, None),
                                      menu_acessado=(True, 'menu_trocar_mesa'))
                        result = send_text_message(recipient_id, get_mensagem('mesa2'))
                    elif payload == 'menu_nada_fazer':
                        set_variaveis(recipient_id,
                                      passo=(False, None),
                                      itens_pedido=(False, None),
                                      datetime_pedido=(False, None))
                        result = send_text_message(recipient_id, get_mensagem('encerrar'))
                    elif payload == 'menu_rever_pedido':
                        if len(conversas[recipient_id]['itens_pedido']) > 0:
                            pedidos = None
                            for i, item in enumerate(conversas[recipient_id]['itens_pedido']):
                                if pedidos:
                                    pedidos += '\n'
                                else:
                                    pedidos = ''
                                pedidos += '('+repr(i+1)+'): ' + repr(item['quantidade']) + ' ' + item['descricao']
                            set_variaveis(recipient_id,
                                          passo=(False, None),
                                          itens_pedido=(False, None),
                                          datetime_pedido=(False, None),
                                          menu_acessado=(True, 'menu_rever_pedido'))
                            result = send_text_message(recipient_id, get_mensagem('rever'))
                            result = send_text_message(recipient_id, pedidos)
                        else:
                            result = send_quickreply_message(recipient_id, get_mensagem('rever2'),
                                                             get_quickreply_menu())
                            # TODO pegar os pedidos em aberto do servidor
                    elif payload == 'menu_ajuda' or payload == 'menu_adicionar_item_pedido' or \
                            payload == 'menu_fechar_conta':
                        result = send_text_message(recipient_id, get_mensagem('desenv'))
                    elif conversas[recipient_id]['passo'] == 3 and payload == 'pedir_mais':
                        set_variaveis(recipient_id,
                                      passo=(True, 2),
                                      itens_pedido=(False, None),
                                      datetime_pedido=(False, None))
                        result = send_text_message(recipient_id, get_mensagem('pedido3'))
                    elif conversas[recipient_id]['passo'] == 3 and payload == 'finalizar_pedido':
                        # TODO enviar mensagem para cliente com o que está sendo enviado!!!
                        set_variaveis(recipient_id)
                        result = send_text_message(recipient_id, get_mensagem('enviar'))
        resp = Response('success', status=200, mimetype='text/plain')
        resp.status_code = 200
        return resp


if __name__ == "__main__":
    context = ('fullchain.pem', 'privkey.pem')
    # app.run(host='0.0.0.0', port=80, debug=True)
    app.run(host='0.0.0.0', port=5002, ssl_context=context, threaded=True, debug=True)
