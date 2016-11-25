# -*- coding: utf-8 -*-

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
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
