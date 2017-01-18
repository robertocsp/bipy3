# -*- coding: utf-8 -*-
import requests
import base64
import datetime
import logging
import keys.keys as my_keys
import my_cache.cache as my_cache
try:
    from urllib.parse import parse_qs, urlencode
except ImportError:
    from urlparse import parse_qs
    from urllib import urlencode

logger = logging.getLogger(__name__)
FACEBOOK_GRAPH_URL = "https://graph.facebook.com/v2.7"


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


def fb_request(app_id, path, loja_id, args=None, post_args=None, json=None, files=None, method=None, headers=None):
    args = args or {}

    if post_args is not None or json is not None:
        method = "POST"

    # access_token = my_cache.cache_client.get(loja_id + 'pac')
    access_token = my_keys.FB_APPS[app_id]['pac']
    if access_token is None:
        return
        # access_token = get_page_access_token(loja_id)
        # logger.debug('=========================>>>>> access token call result ' + repr(access_token))
        # if access_token:
        #     my_cache.cache_client.set(loja_id + 'pac', access_token, time=my_cache.EXPIRACAO_CACHE_LOJA)
        # else:
        #     return

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
        logger.error('!!!ERROR!!! ' + repr(response))
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


def post(app_id, loja_id, post_args=None, json=None, files=None, headers=None):
    time_start = datetime.datetime.now().replace(microsecond=0)
    result = fb_request(app_id, '/me/messages', loja_id, post_args=post_args, json=json, files=files, headers=headers)
    delta_t = datetime.datetime.now().replace(microsecond=0) - time_start
    logger.info('>>>>> facebook call delta t ' + repr(delta_t.total_seconds()) + 's')
    logger.debug('=========================>>>>> facebook call result ' + repr(result))
    return result


def get_page_access_token(page_id):
    payload = {'chave_bot_api_interna': my_keys.CHAVE_BOT_API_INTERNA, 'page_id': page_id}
    url = 'http://localhost:8888/marviin/api/rest/page_access_token'
    headers = {'Authorization': 'Basic ' + base64.b64encode(my_keys.SUPER_USER_USER + ':' + my_keys.SUPER_USER_PASSWORD)}
    response = requests.get(url, params=payload, headers=headers)
    res_json = response.json()
    logger.info('>>>>> access token call result ' + repr(res_json))
    if 'success' in res_json and res_json['success'] == True:
        return res_json['access_token']
    return None
