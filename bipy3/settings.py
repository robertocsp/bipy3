"""
Django settings for bipy3 project.

Generated by 'django-admin startproject' using Django 1.8.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


with open(os.path.join(os.path.join(os.path.dirname(BASE_DIR), 'bipy3_conf'), 'keys.txt')) as keys_file:
    for line in keys_file:
        key_value_pair = line.strip().split('=')
        if key_value_pair[0] == 'secret_key':
            SECRET_KEY = key_value_pair[1]
        elif key_value_pair[0] == 'api-secret':
            CHAVE_BOT_API_INTERNA = key_value_pair[1]
        elif key_value_pair[0] == 'app-id':
            FB_APP_ID = key_value_pair[1]
        elif key_value_pair[0] == 'app-secret':
            FB_APP_SECRET = key_value_pair[1]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

LOGIN_URL = '/'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ws4redis',
    'rest_framework',
    'corsheaders',
    'bipy3',
    'dashboard',
    'pedido',
    'cliente',
    'loja',
    'notificacao',
    'fb_acesso',
    'upload_cardapio',
    'relacionamento',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'bipy3.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',

                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                'django.core.context_processors.static',
                'ws4redis.context_processors.default',
            ],
        },
    },
]

WSGI_APPLICATION = 'bipy3.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases
DATABASES = {
     'default': {
         'ENGINE': 'django.db.backends.mysql',
         'OPTIONS': {
             'read_default_file': os.path.join(os.path.join(os.path.dirname(BASE_DIR), 'bipy3_conf'), 'my.cnf'),
         },
     }
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAdminUser',
    # 'PAGE_SIZE': 10,
    )
}

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

WEBSOCKET_URL = '/ws/'

WS4REDIS_HEARTBEAT = '--heartbeat--'

#configuracao para nao persistir as mensagens enviadas via websocket
#quando o valor eh positivo a cada reconexao no canal a ultima mensagem eh sempre enviada novamente para o cliente
#a principio nao vejo necessidade de precisar receber a ultima mensagem enviada pelo canal novamente em um reload de pagina
WS4REDIS_EXPIRE = -1

CORS_ORIGIN_ALLOW_ALL = True

if not os.path.exists(os.path.join(os.path.dirname(BASE_DIR), 'logs')):
    os.makedirs(os.path.join(os.path.dirname(BASE_DIR), 'logs'))
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(os.path.join(os.path.dirname(BASE_DIR), 'logs'), 'debug.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
