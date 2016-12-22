from aescipher import AESCipher
from cliente.models import Cliente
from django.core import signing
from django.conf import settings
import unicodedata


def check_valid_login(request, psid, logger):
    if psid is None and 'psid' not in request.GET:
        logger.error('-=-=-=-=-=-=-=- parametro psid nao encontrado.')
        return False, None
    if psid is not None and 'sessionid' not in request.COOKIES:
        logger.error('-=-=-=-=-=-=-=- sessao invalida. cookie de sessao nao encontrado. encrypt_psid: ' + psid)
        return False, None
    if psid is not None and 'sessionid' in request.COOKIES and 'AUTH_CODE' not in request.session:
        logger.error('-=-=-=-=-=-=-=- sessao invalida. AUTH_CODE nao encontrado na sessao. encrypt_psid: ' + psid)
        return False, None
    if psid is not None and 'sessionid' in request.COOKIES and 'AUTH_CODE' in request.session:
        try:
            signing.loads(request.session['AUTH_CODE'].split('#')[0], max_age=600)  # max ages em segundos (10 minutos)
        except signing.BadSignature:
            logger.error('-=-=-=-=-=-=-=- sessao invalida. codigo de autorizacao expirado, 10 min. '
                         'encrypt_psid: ' + psid)
            return False, None
    if psid is not None:
        logger.debug('-=-=-=-=-=-=-=- key before :: ' + settings.SECRET_KEY[:32])
        key32 = '{: <32}'.format(settings.SECRET_KEY[:32]).encode("utf-8")
        logger.debug('-=-=-=-=-=-=-=- key after :: ' + key32)
        logger.debug('-=-=-=-=-=-=-=- enc psid :: ' + psid)
        n_psid = unicodedata.normalize('NFKD', psid).encode('ascii', 'ignore')
        cipher = AESCipher(key=key32)
        try:
            d_psid = cipher.decrypt(n_psid)
        except TypeError:
            logger.error('-=-=-=-=-=-=-=- encrypt_psid invalido: ' + psid)
            return False, None
    else:
        d_psid = request.GET['psid']
    try:
        cliente = Cliente.objects.select_related('cliente_marviin').get(chave_facebook=d_psid)
    except Cliente.DoesNotExist:
        logger.error('-=-=-=-=-=-=-=- usuario nao encontrado. decrypt_psid: ' + d_psid)
        return False, None
    if cliente.cliente_marviin is None or cliente.cliente_marviin.authorization_code is None:
        logger.error('-=-=-=-=-=-=-=- usuario nao logado. decrypt_psid: ' + d_psid)
        return False, None
    if psid is not None:
        if request.session['AUTH_CODE'] != cliente.cliente_marviin.authorization_code:
            logger.error('-=-=-=-=-=-=-=- codigo de autorizacao invalido. decrypt_psid: ' + d_psid + ' ; '
                         'auth_code sessao: ' + request.session['AUTH_CODE'] + ' ; '
                         'auth_code BD: ' + cliente.cliente_marviin.authorization_code)
            return False, None
    else:
        authorization_code = cliente.cliente_marviin.authorization_code.split('#')[0]
        try:
            signing.loads(authorization_code, max_age=600)  # max ages em segundos (10 minutos)
        except signing.BadSignature:
            logger.error('-=-=-=-=-=-=-=- sessao invalida. codigo de autorizacao expirado, 10 min. '
                         'decrypt_psid: ' + d_psid)
            return False, None
    return True, cliente
