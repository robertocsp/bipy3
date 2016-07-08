# -*- coding: utf-8 -*-
from ws4redis.publisher import RedisPublisher
from ws4redis.redis_store import RedisMessage

redis_publisher = RedisPublisher(facility='foobar', broadcast=True)


class Websocket():

    def __init__(self):
        pass

    def publicar_mensagem(self, mensagem, *args, **kwargs):
        message = RedisMessage(mensagem)
        # and somewhere else
        redis_publisher.publish_message(message)