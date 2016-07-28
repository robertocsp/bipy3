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

from flask import Flask, request, send_from_directory, Response

try:
    from urllib.parse import parse_qs, urlencode
except ImportError:
    from urlparse import parse_qs
    from urllib import urlencode

app = Flask(__name__)
FACEBOOK_GRAPH_URL = "https://graph.facebook.com/v2.7"
TOKEN = "TOKEN"
logging.basicConfig(filename='demoindoorbot.log', level=logging.DEBUG)


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


def get_text_payload(recipient_id, message):
    payload = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'text': message
        }
    }
    return payload


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
    except requests.HTTPError as e:
        response = json.loads(e.read())
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


def send_image(recipient_id, image_path, content_type):
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


def get_buttons_tamanho():
    return [
        {
            'type':'postback',
            'title':u'Média',
            'payload':'1'
        },
        {
            'type': 'postback',
            'title': 'Grande',
            'payload': '2'
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


@app.route('/', defaults={'path': ''})
@app.route('/.well-known/acme-challenge/<path:path>')
def ping(path):
    return send_from_directory('.well-known/acme-challenge', path, as_attachment=False,
                               mimetype='text/plain')


conversas = {}


@app.route("/webhook", methods=['GET', 'POST'])
def hello():
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == 'verificacao-muita-segura-do-demo-indoor-bot':
                return request.args.get("hub.challenge")
        return
    if request.method == 'POST':
        logging.debug(u'INICIO POST')
        output = request.json
        logging.debug(output)
        event = output['entry'][0]['messaging']
        for x in event:
            if x.get('sender') and x['sender']['id']:
                recipient_id = str(x['sender']['id'])
                try:
                    conversas[recipient_id]
                except KeyError:
                    user = get_object(recipient_id)
                    conversas[recipient_id] = {
                        'passo':0,
                        'usuario':user
                    }
                    logging.debug(user)
            if x.get('message') and x['message'].get('text'):
                message = x['message']['text']
                logging.debug('message: '+message)

                logging.debug('debug 1')
                if unicodedata.normalize('NFKD', message).encode('ASCII', 'ignore').lower() == u'ola':
                    logging.debug('debug 2')
                    result = post(json=get_text_payload(recipient_id, u'Olá, ' +
                        conversas[recipient_id]['usuario']['first_name'] + u', me chamo Marvin tudo bem? Por favor, digite o número de'
                        u' sua mesa para iniciarmos seu atendimento.'))
                    logging.debug(result)
                    logging.debug('debug 3')
                    conversas[recipient_id]['passo'] = 1
                elif conversas[recipient_id]['passo'] == 1:
                    result = send_image(recipient_id, 'cardapio01.jpg', 'image/jpeg')
                    logging.debug(result)
                    result = post(json=get_text_payload(recipient_id, u'Excelente, veja o nosso cardápio e digite aqui o que deseja.'
                        u' Ah, quanto mais detalhado melhor. ;)'))
                    logging.debug('debug 4')
                    logging.debug(result)
                    conversas[recipient_id]['passo'] = 2
                elif conversas[recipient_id]['passo'] == 2:
                    result = post(json=get_text_payload(recipient_id, conversas[recipient_id]['usuario']['first_name'] + u', deseja mais'
                        u' alguma coisa?'))
                    conversas[recipient_id]['passo'] = 3
                elif conversas[recipient_id]['passo'] == 3:
                    post(json=get_text_payload(recipient_id, u'Ok, seu pedido já já estará aí.\n'
                        u'Caso queira mais alguma coisa é só me chamar.'))
                    conversas[recipient_id]['passo'] = 4
                else:
                    logging.debug('no success')
                    result = post(json=get_text_payload(recipient_id, u'Desculpe, não entendi.'))
                    logging.debug(result)

        resp = Response('success', status=200, mimetype='text/plain')
        resp.status_code = 200
        return resp
'''
                elif conversas[recipient_id]['passo'] == 4:
                    # não foi possível utilizar por botão (postback), pois não estava aceitando a quantidade de botões
                    result = post(get_text_payload(recipient_id, u'O total do seu pedido ficou em R$42,00, qual será '
                        u'a forma de pagamento? Digite o número da opção desejada.\n1. Dinheiro\n2. Crédito\n3. Débito'
                        u'\n4. Ticket refeição'))
                    conversas[recipient_id]['passo'] = 5
                elif conversas[recipient_id]['passo'] == 5: #
                    result = post(get_text_payload(recipient_id, u'Seu pedido foi concluído com sucesso, anote o número'
                        u' de registro: 723645.'))
                    result = post(get_text_payload(recipient_id, u'A pizzaria XPTO agradece o seu contato e lhe deseja'
                        u' uma boa noite.'))
                    conversas[recipient_id]['passo'] = 6
                else:
                    logging.debug('no success')
                    result = post(get_text_payload(recipient_id, u'Desculpe, não entendi.'))
                    logging.debug(result)
            elif x.get('postback') and x['postback'].get('payload'):
                payload = x['postback']['payload']
                logging.debug(payload)
                if conversas[recipient_id]['passo'] == 2:
                    if payload == '1':
                        tamanho = u'média'
                    else:
                        tamanho = u'grande'
                    result = post(get_text_payload(recipient_id, 'Certo, '+tamanho+' de calabresa, agora me informe quantas'
                        u' pizzas você deseja?'))
                    conversas[recipient_id]['passo'] = 3
                else:
                    logging.debug('no success')
                    result = post(get_text_payload(recipient_id, u'Desculpe, não entendi.'))
                    logging.debug(result)

        resp = Response('success', status=200, mimetype='text/plain')
        resp.status_code = 200
        return resp
'''

if __name__ == "__main__":
    context = ('fullchain.pem', 'privkey.pem')
    # app.run(host='0.0.0.0', port=80, debug=True)
    app.run(host='0.0.0.0', port=5002, ssl_context=context, threaded=True, debug=True)
