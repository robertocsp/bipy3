# -*- coding: utf-8 -*-

import logging


def setup_custom_logger(name, handler, level):
    # formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    # handler = logging.StreamHandler()
    # handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = 0
    return logger
