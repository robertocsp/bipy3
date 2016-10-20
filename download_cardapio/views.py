# -*- coding: utf-8 -*-

from django.http import StreamingHttpResponse, HttpResponse
from wsgiref.util import FileWrapper
from upload_cardapio.models import Cardapio

import mimetypes
import logging
import os
import json

logger = logging.getLogger('django')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARDAPIO_BASE_DIR = os.path.join(BASE_DIR, 'marviin_cardapios')


def download_cardapio(request):
    chave = request.GET['chave']
    pagina = request.GET['pagina']
    cardapio = Cardapio.objects.filter(chave=chave, pagina=pagina)
    if not cardapio:
        response = HttpResponse(json.dumps({'success': False, 'type': 400,
                                            'error': u'Nenhum cardápio encontrado.'}),
                                content_type='application/json')
        response.status_code = 400
        return response
    the_file = os.path.join(os.path.join(CARDAPIO_BASE_DIR, chave + str(cardapio[0].pagina)), cardapio[0].nome)
    filename = os.path.basename(the_file)
    chunk_size = 8192
    response = StreamingHttpResponse(FileWrapper(open(the_file), chunk_size),
                                     content_type=mimetypes.guess_type(the_file)[0])
    response['Content-Length'] = os.path.getsize(the_file)
    response['Content-Disposition'] = "inline; filename=%s" % filename
    return response
