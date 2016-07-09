# -*- coding: utf-8 -*-
from ws4redis.publisher import RedisPublisher
from ws4redis.redis_store import RedisMessage


class Websocket():

    def __init__(self):
        pass

    def publicar_mensagem(self, cliente, mensagem, *args, **kwargs):
        redis_publisher = RedisPublisher(facility=cliente, broadcast=True)
        message = RedisMessage(mensagem)
        # and somewhere else
        redis_publisher.publish_message(message)