#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Configuration for Python built-in logging
"""

import logging

logger = logging.getLogger('nc_coder')
logger.propagate = False


LEVELS = {
    'debug': logging.DEBUG,
    'DEBUG': logging.DEBUG,
    'info': logging.INFO,
    'INFO': logging.INFO,
    'warning': logging.WARNING,
    'WARNING': logging.WARNING,
    'error': logging.ERROR,
    'ERROR': logging.ERROR,
    'critical': logging.CRITICAL,
    'CRITICAL': logging.CRITICAL
}

FORMAT = {
    'default': '%(asctime)s [NC_CODER] %(message)s',
    'DEFAULT': '%(asctime)s [NC_CODER] %(message)s',
    'debug': '%(asctime)s %(levelname)-8s %(module)s %(threadName)s %(lineno)d [NC_CODER] %(message)s',
    'DEBUG': '%(asctime)s %(levelname)-8s %(module)s %(threadName)s %(lineno)d [NC_CODER] %(message)s',
    'info': '%(asctime)s %(levelname)-8s %(module)s [NC_CODER] %(message)s',
    'INFO': '%(asctime)s %(levelname)-8s %(module)s [NC_CODER] %(message)s'
}


def conf_logger(level):
    logger.setLevel(LEVELS[level])
    handler = logging.StreamHandler()
    formatter = logging.Formatter(FORMAT.get(level, FORMAT['default']))

    handler.setFormatter(formatter)
    logger.addHandler(handler)
