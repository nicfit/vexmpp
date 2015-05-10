# -*- coding: utf-8 -*-
import logging
import logging.config
from io import StringIO

DEFAULT_FORMAT = "<%(name)s>: %(asctime)s [%(levelname)s]: %(message)s"
METRICS_FORMAT = "<metrics time='%(asctime)s'>%(message)s</metrics>"
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
keys = console, metrics

[formatters]
keys = generic, metrics

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

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = {generic_format}

[logger_vexmpp.metrics]
level = NOTSET
qualname = vexmpp.metrics
handlers = metrics
propagate = 0

[handler_metrics]
class = FileHandler
args = ("vexmpp-metrics.log", "w", None, True)
level = NOTSET
formatter = metrics

[formatter_metrics]
format = {metrics_format}

""".format(generic_format=DEFAULT_FORMAT, metrics_format=METRICS_FORMAT)


logging.setLoggerClass(Logger)
log = logging.getLogger(MAIN_LOGGER)
logging.config.fileConfig(StringIO(DEFAULT_LOGGING_CONFIG))
