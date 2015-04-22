# -*- coding: utf-8 -*-
import logging
import logging.config
from io import StringIO

DEFAULT_FORMAT = "<%(name)s>: %(asctime)s [%(levelname)s]: %(message)s"
MAIN_LOGGER = "vexmpp"

# Add a verbose level more than INFO and less than DEBUG
logging.VERBOSE = logging.DEBUG + 1
logging.addLevelName(logging.VERBOSE, "VERBOSE")


class Logger(logging.Logger):
    '''Base class for all loggers'''

    def __init__(self, name):
        logging.Logger.__init__(self, name)

        # Using propogation of child to parent, by default
        self.propagate = True
        self.setLevel(logging.NOTSET)

    def verbose(self, msg, *args, **kwargs):
        '''Log \a msg at 'verbose' level, debug < verbose < info'''
        self.log(logging.VERBOSE, msg, *args, **kwargs)

LEVELS = (logging.DEBUG, logging.VERBOSE, logging.INFO,
          logging.WARNING, logging.ERROR, logging.CRITICAL)

DEFAULT_LOGGING_CONFIG = """
###
#logging configuration
#https://docs.python.org/3/library/logging.config.html#configuration-file-format
###

[loggers]
keys = root, vexmpp, vexmpp.metrics

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_vexmpp]
level = NOTSET
qualname = vexmpp
; When adding more specific handlers than what exists on the root you'll
; likely want to set propagate to false.
handlers =
propagate = 1

[logger_vexmpp.metrics]
level = NOTSET
qualname = vexmpp.metrics
; When adding more specific handlers than what exists on the root you'll
; likely want to set propagate to false.
handlers =
propagate = 1

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(generic_format)s
""" % {"generic_format": DEFAULT_FORMAT,
       }


logging.setLoggerClass(Logger)
log = logging.getLogger(MAIN_LOGGER)
logging.config.fileConfig(StringIO(DEFAULT_LOGGING_CONFIG))
