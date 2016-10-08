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

import logging
import os
import json
import shutil

logger = logging.getLogger('django')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDAPIO_BASE_DIR = os.path.join(os.path.join(os.path.join(
    os.path.join(os.path.join(os.path.dirname(BASE_DIR), 'bipy3'), 'bipy3'), 'static'), 'marviin'), 'cardapios')


@login_required
def upload(request):
    id_loja = request.session['id_loja']
    cardapios = Cardapio.objects.filter(loja=id_loja)
    if not cardapios:
        cardapios = []
    return render_to_response('upload.html', {'cardapios': cardapios},
                              context_instance=RequestContext(request))


@method_decorator(my_login_required, name='dispatch')
class FileFieldView(FormView):
    form_class = UploadCardapioForm

    def post(self, request, *args, **kwargs):
        id_loja = request.session['id_loja']
        if 'action' in request.POST and request.POST['action'] == 'delete':
            resultado = self.delete_cardapio(request, id_loja)
            return resultado
        if Cardapio.objects.filter(loja=id_loja).count() > 1:
            response = HttpResponse(json.dumps({'success': False, 'type': 400,
                                                'error': u'Só são permitidos 2 arquivos de imagem.'}),
                                    content_type='application/json')
            response.status_code = 400
            return response
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('cardapios')
        failure_message = None
        if form.is_valid():
            for idx, f in enumerate(files):
                if idx > 1:
                    if not failure_message:
                        failure_message = ''
                    else:
                        failure_message += ' '
                    failure_message += 'O arquivo "' + f.name + '" foi descartado, pois ultrapassa o limite de 2 ' \
                                                               'arquivos.'
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
                        Cardapio.objects.get(chave=file_directory, loja=id_loja)
                    except Cardapio.DoesNotExist:
                        cardapio = Cardapio()
                        break
                file_dir_path = os.path.join(CARDAPIO_BASE_DIR, file_directory)
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
                cardapio.nome = f.name
                cardapio.tamanho = f.size
                cardapio.caminho = '/static/marviin/cardapios/' + file_directory + '/' + f.name
                cardapio.loja_id = id_loja
                cardapio.save()
            cardapios = Cardapio.objects.filter(loja=id_loja)
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
        Cardapio.objects.filter(chave=dir_to_delete, loja=id_loja).delete()
        shutil.rmtree(os.path.join(CARDAPIO_BASE_DIR, dir_to_delete))
        return JsonResponse({'success': True})
