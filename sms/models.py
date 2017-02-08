# -*- coding: utf-8 -*-
from django.db import models

# statusCode    00 - Ok
#     01 - Scheduled
#     02 - Sent
#     03 - Delivered
#     04 - Not Received
#     05 - Blocked - No Coverage
#     06 - Blocked - Black listed
#     07 - Blocked - Invalid Number
#     08 - Blocked - Content not allowed
#     08 - Blocked - Message Expired
#     09 - Blocked
#     10 - Error
# detailCode    000 - Message Sent
#     002 - Message successfully canceled
#     010 - Empty message content
#     011 - Message body invalid
#     012 - Message content overflow
#     013 - Incorrect or incomplete ‘to’ mobile number
#     014 - Empty ‘to’ mobile number
#     015 - Scheduling date invalid or incorrect
#     016 - ID overflow
#     017 - Parameter ‘url’ is invalid or incorrect
#     018 - Field ‘from’ invalid
#     021 - ‘id’ fieldismandatory
#     080 - Message with same ID already sent
#     100 - Message Queued
#     110 - Message sent to operator
#     111 - Message confirmation unavailable
#     120 - Message received by mobile
#     130 - Message blocked
#     131 - Message blocked by predictive cleansing
#     132 - Message already canceled
#     133 - Message content in analysis
#     134 - Message blocked by forbidden content
#     135 - Aggregate is Invalid or Inactive
#     136 - Message expired
#     140 - Mobile number not covered
#     141 - International sending not allowed
#     145 - Inactive mobile number
#     150 - Message expired in operator
#     160 - Operator network error
#     161 - Message rejected by operator
#     162 - Message cancelled or blocked by operator
#     170 - Bad message
#     171 - Bad number
#     172 - Missing parameter
#     180 - Message ID notfound
#     190 - Unknown error
#     200 - Messages Sent
#     210 - Messages scheduled but Account Limit Reached
#     240 - File empty or not sent
#     241 - File too large
#     242 - File readerror
#     300 - Received messages found
#     301 - No received messages found
#     400 - Entity saved
#     900 - Authentication error
#     901 - Account type not support this operation.
#     990 - Account Limit Reached – Please contact support
#     998 - Wrong operation requested
#     999 - Unknown Error


class Enviado(models.Model):
    id = models.CharField(max_length=50, primary_key=True, editable=False)
    celular = models.CharField(max_length=30, null=True, blank=True)
    conteudo = models.CharField(max_length=160, null=True, blank=True)
    data_hora_envio = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(blank=True, null=True)
    retorno_integracao = models.CharField(max_length=200, null=True, blank=True)
