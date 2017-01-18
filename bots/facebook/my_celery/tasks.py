# -*- coding: utf-8 -*-

import requests
import base64
import json
import time
import keys.keys as my_keys
import facebook.facebook as fb
from celery import Celery  # usar shared_task em caso do celery app nao ficar no arquivo de tarefas
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
fb.logger.parent = logger
celery_app = Celery(__name__, broker='amqp://rabbitbot:rabbitbot@localhost/rabbitbotvhost', backend='rpc://')
ROBOT_ICON = u'\U0001f4bb'


def make_celery(app, vhost):
    _celery_app = Celery(app.import_name, broker='amqp://rabbitbot:rabbitbot@localhost/' + vhost, backend='rpc://')
    _celery_app.conf.update(app.config)
    taskbase = _celery_app.Task

    class ContextTask(taskbase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return taskbase.__call__(self, *args, **kwargs)

    _celery_app.Task = ContextTask
    return _celery_app


@celery_app.task(bind=True, soft_time_limit=7)
def get_object(self, app_id, fb_id, loja_id, **args):
    return fb.fb_request(app_id, '/' + fb_id, loja_id, args=args)


def send_image_message(app_id, sender_id, loja_id, image_path, content_type):
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
    return fb.post(app_id, loja_id, post_args=payload, files=multipart_data)


@celery_app.task(bind=True, soft_time_limit=7)
def send_image_url_message(self, app_id, sender_id, loja_id, url, icon=ROBOT_ICON):
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
    return fb.post(app_id, loja_id, json=payload)


@celery_app.task(bind=True, soft_time_limit=7)
def send_button_message(self, app_id, sender_id, loja_id, text, buttons):
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
    return fb.post(app_id, loja_id, json=payload)


@celery_app.task(bind=True, soft_time_limit=7)
def send_text_message(self, app_id, sender_id, loja_id, text, icon=ROBOT_ICON):
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
    logger.debug(repr(payload))
    return fb.post(app_id, loja_id, json=payload)


@celery_app.task(bind=True, soft_time_limit=7)
def send_quickreply_message(self, app_id, sender_id, loja_id, text, quick_replies, icon=ROBOT_ICON):
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
    return fb.post(app_id, loja_id, json=payload)


@celery_app.task(bind=True, soft_time_limit=7)
def send_generic_message(self, app_id, sender_id, loja_id, elements):
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
    logger.debug(repr(payload))
    return fb.post(app_id, loja_id, json=payload)


@celery_app.task(bind=True, soft_time_limit=10)
def link_psid_marviin(self, user_id, auth_code):
    data = {}
    pass
    data['chave_bot_api_interna'] = my_keys.CHAVE_BOT_API_INTERNA
    data['psid'] = user_id
    data['auth_code'] = auth_code
    url = 'http://localhost:8888/marviin/api/rest/link_to_marviin'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(
                   my_keys.SUPER_USER_USER + ':' + my_keys.SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    json_response = response.json()
    logger.info(repr(response))
    return json_response['success']


@celery_app.task(bind=True, soft_time_limit=10)
def log_out_marviin(self, user_id, auth_code):
    data = {}
    pass
    data['chave_bot_api_interna'] = my_keys.CHAVE_BOT_API_INTERNA
    data['psid'] = user_id
    data['auth_code'] = auth_code
    url = 'http://localhost:8888/marviin/api/rest/log_out'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(
                   my_keys.SUPER_USER_USER + ':' + my_keys.SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    json_response = response.json()
    logger.info(repr(response))
    return json_response['success']


@celery_app.task(bind=True, soft_time_limit=10)
def check_login_valid(self, user_id):
    data = {}
    pass
    data['chave_bot_api_interna'] = my_keys.CHAVE_BOT_API_INTERNA
    data['psid'] = user_id
    url = 'http://localhost:8888/marviin/api/rest/check_login_valid'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(
                   my_keys.SUPER_USER_USER + ':' + my_keys.SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    json_response = response.json()
    logger.info(repr(response))
    return json_response['success']


@celery_app.task(bind=True, soft_time_limit=10)
def get_cardapio(self, loja_id):
    data = {}
    pass
    data['chave_bot_api_interna'] = my_keys.CHAVE_BOT_API_INTERNA
    data['id_loja'] = loja_id
    url = 'http://localhost:8888/marviin/api/rest/cardapio'
    response = requests.get(url, auth=(my_keys.SUPER_USER_USER, my_keys.SUPER_USER_PASSWORD), params=data)
    json_response = response.json()
    logger.info(repr(json_response))
    if json_response['success']:
        if len(json_response['cardapio']) > 0:
            return json_response['cardapio']
    return None


@celery_app.task(bind=True, soft_time_limit=10)
def touch_cliente(self, sender_id):
    data = {}
    pass
    data['chave_bot_api_interna'] = my_keys.CHAVE_BOT_API_INTERNA
    url = 'http://localhost:8888/marviin/api/rest/cliente/' + sender_id + '/touch'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(
                   my_keys.SUPER_USER_USER + ':' + my_keys.SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    logger.info(repr(response))


@celery_app.task(bind=True, soft_time_limit=10)
def salva_se_nao_existir(self, sender_id, loja_id, user):
    data = {}
    pass
    data['chave_bot_api_interna'] = my_keys.CHAVE_BOT_API_INTERNA
    data['id_cliente'] = sender_id
    data['id_loja'] = loja_id
    data['nome_cliente'] = user['first_name'] + ' ' + user['last_name']
    data['foto_cliente'] = user['profile_pic']
    data['genero'] = user['gender']
    url = 'http://localhost:8888/marviin/api/rest/cliente'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(
                   my_keys.SUPER_USER_USER + ':' + my_keys.SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    logger.info(repr(response))


@celery_app.task(bind=True, soft_time_limit=10)
def enviar_pedido(self, app_id, sender_id, loja_id, conversa):
    if conversa['mesa'] is None:
        return
    data = {}
    pass
    data['chave_bot_api_interna'] = my_keys.CHAVE_BOT_API_INTERNA
    data['id_loja'] = loja_id
    data['app'] = app_id
    data['origem'] = 'fbmessenger'
    data['id_cliente'] = sender_id
    data['nome_cliente'] = conversa['usuario']['first_name'] + ' ' + conversa['usuario']['last_name']
    data['foto_cliente'] = conversa['usuario']['profile_pic']
    data['itens_pedido'] = conversa['itens_pedido']
    data['mesa'] = conversa['mesa'][0]
    url = 'http://localhost:8888/marviin/api/rest/pedido'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(
                   my_keys.SUPER_USER_USER + ':' + my_keys.SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    logger.info(repr(response))


@celery_app.task(bind=True, soft_time_limit=10)
def envia_resposta(self, conversa, loja_id, sender_id, message):
    data = {}
    pass
    data['chave_bot_api_interna'] = my_keys.CHAVE_BOT_API_INTERNA
    data['id_loja'] = loja_id
    data['id_cliente'] = sender_id
    data['origem'] = 'chat'
    data['nome_cliente'] = conversa['usuario']['first_name'] + ' ' + conversa['usuario']['last_name']
    data['foto_cliente'] = conversa['usuario']['profile_pic']
    data['cliente'] = message
    data['uid'] = conversa['uid']
    url = 'http://localhost:8888/marviin/api/rest/mensagem_bot'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(
                   my_keys.SUPER_USER_USER + ':' + my_keys.SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    logger.info(repr(response))


@celery_app.task(bind=True, soft_time_limit=10)
def troca_mesa_dashboard(self, sender_id, loja_id, conversa):
    data = {}
    pass
    data['chave_bot_api_interna'] = my_keys.CHAVE_BOT_API_INTERNA
    data['id_loja'] = loja_id
    data['id_cliente'] = sender_id
    data['mesa'] = conversa['mesa'][0]
    if len(conversa['mesa']) == 2:
        data['mesa_anterior'] = conversa['mesa'][1]
    url = 'http://localhost:8888/marviin/api/rest/troca_mesa'
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(
                   my_keys.SUPER_USER_USER + ':' + my_keys.SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    logger.info(repr(response))


@celery_app.task(bind=True, soft_time_limit=10)
def notificacao_dashboard(self, sender_id, loja_id, conversa, metodo_api):
    data = {}
    pass
    data['chave_bot_api_interna'] = my_keys.CHAVE_BOT_API_INTERNA
    data['id_loja'] = loja_id
    data['id_cliente'] = sender_id
    data['nome_cliente'] = conversa['usuario']['first_name'] + ' ' + conversa['usuario']['last_name']
    data['foto_cliente'] = conversa['usuario']['profile_pic']
    data['mesa'] = conversa['mesa'][0]
    url = 'http://localhost:8888/marviin/api/rest/pede_'+metodo_api
    headers = {'content-type': 'application/json',
               'Authorization': 'Basic ' + base64.b64encode(
                   my_keys.SUPER_USER_USER + ':' + my_keys.SUPER_USER_PASSWORD)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    logger.info(repr(response))


@celery_app.task(bind=True, soft_time_limit=1, default_retry_delay=0, max_retries=3)
def teste_tarefa(self):
    try:
        logger.info('>>> tarefa iniciada ::')
        time.sleep(4)
        logger.info('>>> tarefa concluida ::')
    except SoftTimeLimitExceeded as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True)
def error_handler(self, uuid):
    result = self.app.AsyncResult(uuid)
    logger.info('Task {0} raised exception: {1!r}\n{2!r}'.format(uuid, result.result, result.traceback))
