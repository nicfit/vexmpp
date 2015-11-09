# -*- coding: utf-8 -*-
import sys
import logging
import logging.config
import argparse
from pathlib import Path

LOG_FORMAT = "[%(asctime)s] %(name)-25s [%(levelname)-8s]: %(message)s"
METRICS_FORMAT = "<metrics time='%(asctime)s'>%(message)s</metrics>"

logging.VERBOSE = logging.DEBUG + 1
logging.addLevelName(logging.VERBOSE, "VERBOSE")
LEVELS = [logging.DEBUG, logging.VERBOSE, logging.INFO,
          logging.WARNING, logging.ERROR, logging.CRITICAL]
LEVEL_NAMES = [logging.getLevelName(l).lower() for l in LEVELS]


class Logger(logging.getLoggerClass()):
    '''Base class for all package loggers'''

    def __init__(self, name):
        super().__init__(name)

        # Using propogation of child to parent, by default
        self.propagate = True
        self.setLevel(logging.NOTSET)

    def verbose(self, msg, *args, **kwargs):
        '''Log \a msg at 'verbose' level, debug < verbose < info'''
        self.log(logging.VERBOSE, msg, *args, **kwargs)


def getLogger(name):
    OrigLoggerClass = logging.getLoggerClass()
    try:
        logging.setLoggerClass(Logger)
        return logging.getLogger(name)
    finally:
        logging.setLoggerClass(OrigLoggerClass)


log = getLogger("vexmpp")
log.addHandler(logging.NullHandler())


def simpleConfig(level=logging.WARNING):
    '''Configures the ``vexmpp`` logger with a
    simple stdout logging handler set to ``level``.'''
    global log

    log.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT)
    console = logging.StreamHandler()
    console.setFormatter(formatter)

    log.handlers.clear()
    log.addHandler(console)


def _optSplit(opt):
    if ':' in opt:
        first, second = opt.split(":")
    else:
        first, second = None, opt
    return first, second


class LogLevelAction(argparse._AppendAction):
    def __call__(self, parser, namespace, values, option_string=None):
        log_name, log_level = _optSplit(values)

        if log_level.lower() not in LEVEL_NAMES:
            raise ValueError("Unknown log level: {}".format(log_level))

        logger, level = (logging.getLogger(log_name),
                         getattr(logging, log_level.upper()))
        logger.setLevel(level)

        values = tuple([logger, level])
        super().__call__(parser, namespace, values, option_string=option_string)


class LogFileAction(argparse._AppendAction):
    def __call__(self, parser, namespace, values, option_string=None):
        log_name, logpath = _optSplit(values)

        logger, logpath = logging.getLogger(log_name), logpath

        formatter = None
        handlers_logger = None
        if logger.hasHandlers():
            # Find the logger with the actual handlers attached
            handlers_logger = logger if logger.handlers else logger.parent
            while not handlers_logger.handlers:
                handlers_logger = handlers_logger.parent

            assert(handlers_logger)
            for h in list(handlers_logger.handlers):
                formatter = h.formatter
                handlers_logger.removeHandler(h)
        else:
            handlers_logger = logger

        if logpath in ("stdout", "stderr"):
            h = logging.StreamHandler(stream=sys.stdout if "out" in logpath
                                                        else sys.stderr)
        elif logpath == "null":
            h = logging.NullHandler()
        else:
            h = logging.FileHandler(logpath)

        h.setFormatter(formatter)
        handlers_logger.addHandler(h)

        values = tuple([logger, h])
        super().__call__(parser, namespace, values, option_string=option_string)


def addCommandLineArgs(arg_parser):
    arg_parser.register("action", "log_levels", LogLevelAction)
    arg_parser.register("action", "log_files", LogFileAction)

    group = arg_parser.add_argument_group("Logging options")
    group.add_argument(
        "-l", "--log-level", dest="log_levels",
        action="log_levels", metavar="LOGGER:LEVEL", default=[],
        help="Set logging levels (the option may be specified multiple "
             "times). The level of a specific logger may be set with "
             "the syntax LOGGER:LEVEL, but LOGGER is optional so "
             "if only LEVEL is given it applies to the root logger. "
             "Valid level names are: %s" % ", ".join(LEVEL_NAMES))

    group.add_argument(
        "-L", "--log-file", dest="log_files",
        action="log_files", metavar="LOGGER:FILE", default=[],
        help="Set log files (the option may be specified multiple "
             "times). The level of a specific logger may be set with "
             "the syntax LOGGER:FILE, but LOGGER is optional so "
             "if only FILE is given it applies to the root logger. "
             "The special FILE values 'stdout', 'stderr', and 'null' "
             "result on logging to the console, or /dev/null in the "
             "latter case.")

DEFAULT_FILE_CONFIG = """
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
format = {default_format}

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

""".format(default_format=LOG_FORMAT, metrics_format=METRICS_FORMAT)
