# -*- coding: utf-8 -*-

import logging
from logging.handlers import RotatingFileHandler
from logging import Formatter
from logger import logger

logging_handler = RotatingFileHandler(filename='/var/log/bot/demoindoorbot.log', maxBytes=5*1024*1024, backupCount=2)
logging_handler.setFormatter(Formatter(fmt='%(asctime)s,%(levelname)s,%(module)s,%(threadName)s,%(processName)s ::: '
                                           '%(message)s'))
app_log = logger.setup_custom_logger('demobot', logging_handler, logging.DEBUG)


