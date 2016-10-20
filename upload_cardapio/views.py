# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from bipy3.auth.my_ajax_decorators import my_login_required
from django.http import JsonResponse
from django.views.generic.edit import FormView
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.utils.crypto import get_random_string
from upload_cardapio.models import Cardapio
from .forms import UploadCardapioForm
from notificacao.models import Notificacao

import logging
import os
import json
import shutil

logger = logging.getLogger('django')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARDAPIO_BASE_DIR = os.path.join(BASE_DIR, 'marviin_cardapios')


@login_required
def upload(request):
    id_loja = request.session['id_loja']
    cardapios = Cardapio.objects.filter(loja=id_loja, pagina=1)
    if not cardapios:
        cardapios = []
    cardapios2 = Cardapio.objects.filter(loja=id_loja, pagina=2)
    if not cardapios2:
        cardapios2 = []
    notificacoes = Notificacao.objects.filter(loja=id_loja, dt_visto__isnull=True).order_by('dt_criado')
    return render_to_response('upload.html', {'cardapios': cardapios, 'cardapios2': cardapios2,
                                              'notificacoes': notificacoes},
                              context_instance=RequestContext(request))


@method_decorator(my_login_required, name='dispatch')
class FileFieldView(FormView):
    form_class = UploadCardapioForm

    def post(self, request, *args, **kwargs):
        id_loja = request.session['id_loja']
        if 'action' in request.POST and request.POST['action'] == 'delete':
            resultado = self.delete_cardapio(request, id_loja)
            return resultado
        if 'page' not in request.POST:
            response = HttpResponse(json.dumps({'success': False, 'type': 400,
                                                'error': u'Chamada inválida, recarregue a página e repita a '
                                                         u'operação.'}),
                                    content_type='application/json')
            response.status_code = 400
            return response
        page = request.POST['page']
        if Cardapio.objects.filter(loja=id_loja, pagina=page).count() > 0:
            response = HttpResponse(json.dumps({'success': False, 'type': 400,
                                                'error': u'Só é permitido 1 arquivo por página.'}),
                                    content_type='application/json')
            response.status_code = 400
            return response
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('cardapio')
        failure_message = None
        if form.is_valid():
            for idx, f in enumerate(files):
                if idx > 0:
                    if not failure_message:
                        failure_message = ''
                    else:
                        failure_message += ' '
                    failure_message += 'O arquivo "' + f.name + '" foi descartado, pois ultrapassa o limite de 1 ' \
                                       'arquivo da página '+repr(page)+'.'
                    continue
                if f.size > 1048576:
                    if not failure_message:
                        failure_message = ''
                    else:
                        failure_message += ' '
                    failure_message += 'O arquivo "' + f.name + '" foi descartado, pois ultrapassa o tamanho de 1 MB.'
                    continue
                while True:
                    file_directory = get_random_string(length=32)
                    try:
                        Cardapio.objects.get(chave=file_directory, pagina=page)
                    except Cardapio.DoesNotExist:
                        cardapio = Cardapio()
                        break
                file_dir_path = os.path.join(CARDAPIO_BASE_DIR, file_directory + str(page))
                try:
                    os.makedirs(file_dir_path)
                except OSError:
                    if not os.path.isdir(file_dir_path):
                        raise
                with open(os.path.join(file_dir_path, f.name), 'wb+') as \
                        destination:
                    for chunk in f.chunks():
                        destination.write(chunk)
                cardapio.chave = file_directory
                cardapio.pagina = page
                cardapio.nome = f.name
                cardapio.tamanho = f.size
                cardapio.caminho = '/download-cardapio/?chave=' + file_directory + '&pagina=' + str(page)
                cardapio.loja_id = id_loja
                cardapio.save()
            cardapios = Cardapio.objects.filter(loja=id_loja, pagina=page)
            if cardapios:
                success_files = [cardapio.as_dict() for cardapio in cardapios]
            else:
                success_files = []
            if not failure_message:
                return JsonResponse({'success': True, 'success_files': success_files})
            else:
                response = HttpResponse(json.dumps({'success': False, 'type': 200,
                                                    'error': failure_message, 'success_files': success_files}),
                                        content_type='application/json')
                response.status_code = 400
                return response
        else:
            response = HttpResponse(json.dumps({'success': False, 'type': 400,
                                                'error': u'Não foi possível realizar sua ação, tente em instantes.'}),
                                    content_type='application/json')
            response.status_code = 400
            return response

    def delete_cardapio(self, request, id_loja):
        dir_to_delete = request.POST['key']
        page = request.POST['page']
        Cardapio.objects.filter(chave=dir_to_delete, loja=id_loja, pagina=page).delete()
        shutil.rmtree(os.path.join(CARDAPIO_BASE_DIR, dir_to_delete + str(page)))
        return JsonResponse({'success': True})
