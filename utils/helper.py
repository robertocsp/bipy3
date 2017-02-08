# -*- coding: utf-8 -*-
import re


def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)


def valida_senha(senha):
    if len(senha) < 6 or \
       re.search(r'[a-z]', senha) is None or \
       re.search(r'[A-Z]', senha) is None or \
       re.search(r'[\d]', senha) is None or \
       re.search(r'[^a-zA-Z\d]', senha) is None:
        return False
    return True


def digitos(valor):
    return re.sub(r'\D', '', valor)
