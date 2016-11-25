# -*- coding: utf-8 -*-

import memcache


EXPIRACAO_CACHE_CONVERSA = 60 * 60 * 2  # 2 horas
EXPIRACAO_CACHE_LOCK = 15  # tempo de vida do lock é de 15 segundos, no caso de um erro.
EXPIRACAO_CACHE_LOJA = 60 * 60 * 24 * 30  # 30 dias

cache_client = memcache.Client(['127.0.0.1:11211'])
cache_entry_prefix = ''
