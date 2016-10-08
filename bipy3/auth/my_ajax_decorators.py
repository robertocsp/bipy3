# -*- coding: utf-8 -*-

from functools import wraps

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url
from django.utils import six
from django.utils.decorators import available_attrs
from django.http import HttpResponse

import json


def my_user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request):
                return view_func(request, *args, **kwargs)
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            response = HttpResponse(json.dumps({'success': False, 'type': 403,
                                                'error': u'Sessão inválida. Realize o login novamente.',
                                                'next_field_name': redirect_field_name,
                                                'login_url': resolved_login_url}),
                                    content_type='application/json')
            response.status_code = 403
            return response
        return _wrapped_view
    return decorator


def my_login_required(function=None, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    def check_valid_session(request):
        def user_auth_func(u): return u.is_authenticated()
        if user_auth_func(request.user) and 'id_loja' in request.session:
            return True
        return False

    actual_decorator = my_user_passes_test(
        check_valid_session,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def my_permission_required(perm, login_url=None, raise_exception=False):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled, redirecting to the log-in page if necessary.
    If the raise_exception parameter is given the PermissionDenied exception
    is raised.
    """
    def check_perms(request):
        if isinstance(perm, six.string_types):
            perms = (perm, )
        else:
            perms = perm
        # First check if the user has the permission (even anon users)
        if request.user.has_perms(perms):
            return True
        # In case the 403 handler should be called raise the exception
        if raise_exception:
            raise PermissionDenied
        # As the last resort, show the login form
        return False
    return my_user_passes_test(check_perms, login_url=login_url)
