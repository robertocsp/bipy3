# -*- coding: utf-8 -*-
import json
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import JSONParser
from rest_framework import views
from rest_framework.response import Response
from marvinpub.websocket import ws


class EnviarPedidoView(views.APIView):
    permission_classes = (IsAdminUser,)
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        mensagem = request.data.get('mensagem', None)
        if mensagem:
            websocket = ws.Websocket()
            websocket.publicar_mensagem(mensagem)
            return Response({"success": True})
        else:
            return Response({"success": False})