# -*- coding: utf-8 -*-
import sys
import time
import random
import asyncio
import logging
import argparse
import functools
from enum import Enum
from operator import attrgetter
from ipaddress import ip_address
from configparser import ConfigParser

import aiodns

from .log import LEVELS

log = logging.getLogger(__name__)


class benchmark(object):
    '''A context manager for taking timing blocks of code.'''

    def __init__(self, name=None):
        '''If *name* is provided the ``__exit__`` method will print this string
        along with the total elapsed time.'''
        self.name = name
        self.timer_stats = {}

    def __enter__(self):
        '''Returns a dict with the "start" time. By the __exit__ returns the
        keys "end" and "total" contain those times.'''
        self.start = time.time()
        self.timer_stats["start"] = self.start
        return self.timer_stats

    def __exit__(self, ty, val, tb):
        end = time.time()
        self.timer_stats["end"] = end
        self.timer_stats["total"] = end - self.start
        if self.name:
            print("%s : %0.3f seconds" % (self.name, self.timer_stats["total"]))
        return False


def signalEvent(callbacks, event, *args, **kwargs):
    log.debug("Invoking signal %s" % event)
    if callbacks:
        func = getattr(callbacks, event)
        asyncio.get_event_loop().call_soon(
                functools.partial(func, *args, **kwargs))
    else:
        log.debug("No callbacks set")


class ArgumentParser(argparse.ArgumentParser):
    class ConfigOpt(Enum):
        none = 0
        option = 1
        argument = 2

    def __init__(self, add_logging_opts=True, config_opts=ConfigOpt.none,
                 config_required=False, sample_config=None,
                 config_class=None, config_args=None,
                 add_debug_opts=True,
                 **kwargs):

        kwargs["add_help"] = True
        super().__init__(**kwargs)

        if add_logging_opts:
            level_names = [logging.getLevelName(l).lower() for l in LEVELS]
            group = self.add_argument_group("Logging options")
            group.add_argument(
                "-l", "--log-level", dest="log_levels",
                action="append", metavar="LOGGER:LEVEL", default=[],
                help="Set logging levels (the option may be specified multiple "
                     "times). The level of a specific logger may be set with "
                     "the syntax LOGGER:LEVEL, but LOGGER is optional so "
                     "if only LEVEL is given it applies to the root logger. "
                     "Valid level names are: %s" % ", ".join(level_names))

            group.add_argument(
                "-L", "--log-file", dest="log_files",
                action="append", metavar="LOGGER:FILE", default=[],
                help="Set log files (the option may be specified multiple "
                     "times). The level of a specific logger may be set with "
                     "the syntax LOGGER:FILE, but LOGGER is optional so "
                     "if only FILE is given it applies to the root logger. "
                     "The special FILE values 'stdout', 'stderr', and 'null' "
                     "result on logging to the console, or /dev/null in the "
                     "latter case.")

        self._ConfigParser = config_class or ConfigParser
        self._config_args = config_args or tuple([])

        if config_opts != self.ConfigOpt.none:
            group = self.add_argument_group("Configuration options")

            # We don't set this in the parser because then we could not use
            # --example-config without a -c.
            self._config_required = config_required

            if config_opts == self.ConfigOpt.option:
                group.add_argument("-c", "--config", dest="config_file",
                                   metavar="FILENAME",
                                   help="Configuration file (ini file format).")
            else:
                self.add_argument("config_file",
                                  help="Configuration file (ini file format).")

            group.add_argument("-o", dest="config_overrides", action="append",
                               default=[], metavar="SECTION:OPTION=VALUE",
                               help="Overrides the values for configuration "
                                    "OPTION in [SECTION].")

            if sample_config:
                self._sample_config = sample_config
                group.add_argument("--sample-config", dest="__sample_config",
                                   action="store_true",
                                   help="Output a sample configuration file.")

        if add_debug_opts:
            group = self.add_argument_group("Debugging options")
            group.add_argument("--pdb", action="store_true", dest="debug_pdb",
                               help="Invoke pdb (or ipdb if available) on "
                                    "uncaught exceptions.")

    def _handleConfigFileOpts(self, args):
        if "config_file" in args:
            config_opt = args.config_file
            if not config_opt and self._config_required:
                self.error("Configuration (-c/--config) required.")
            elif config_opt:
                cfg_parser = self._ConfigParser(*self._config_args)
                try:
                    cfg_parser.read([config_opt])

                    for override in args.config_overrides:
                         key, val = override.split('=')
                         sect, opt = key.split(':')
                         cfg_parser.set(sect, opt, val)

                    logging.config.fileConfig(cfg_parser)
                except Exception as ex:
                    self.error("Configuration file error: %s" % str(ex))

                args.config_obj = cfg_parser

    def _handleLoggingOpts(self, args):
        def _splitOpt(_opt):
            if ':' in _opt:
                first, second = _opt.split(":")
            else:
                first, second = None, opt
            return logging.getLogger(first), second

        # Log level setting
        for opt in args.log_levels:
            logger, level = _splitOpt(opt)

            level = getattr(logging, level.upper())
            logger.setLevel(level)

        # Log file settings
        for opt in args.log_files:
            logger, filepath = _splitOpt(opt)

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

            if filepath in ("stdout", "stderr"):
                new_handler = logging.StreamHandler(
                        stream=sys.stdout if "out" in filepath else sys.stderr)
            elif filepath == "null":
                new_handler = logging.NullHandler()
            else:
                new_handler = logging.FileHandler(filepath)

            new_handler.setFormatter(formatter)
            handlers_logger.addHandler(new_handler)

    def parse_args(self, args=None, namespace=None):

        # Print example config and exit, if requested. Done before actually
        # parsing to handle even without required arguments.
        if "--sample-config" in (args or sys.argv):
            print(self._sample_config)
            self.exit()

        parsed_args = super().parse_args(args, namespace)

        # Handle config file option, parses and sets'parsed_args.config_obj'.
        # This call may not return.
        self._handleConfigFileOpts(parsed_args)

        # Process log level opts last, they override any any config file.
        try:
            self._handleLoggingOpts(parsed_args)
        except Exception as ex:
            self.error("Logging option error: {}".format(ex))

        return parsed_args


def stripNsFromTag(tag, ns):
    '''Removes ``ns`` from the lxml fully qualified tag name.
    e.g. {namespace}tagname would return tagname.'''
    ns_prefix = "{%s}" % ns
    if tag.startswith(ns_prefix):
        return tag[len(ns_prefix):]
    else:
        raise ValueError("tag is not in namsepace '%s'" % ns)


def formatTime(seconds, total=None, short=False):
    '''
    Format ``seconds`` (number of seconds) as a string representation.
    When ``short`` is False (the default) the format is:

        HH:MM:SS.

    Otherwise, the format is exacly 6 characters long and of the form:

        1w 3d
        2d 4h
        1h 5m
        1m 4s
        15s

    If ``total`` is not None it will also be formatted and
    appended to the result seperated by ' / '.
    '''
    def time_tuple(ts):
        if ts is None or ts < 0:
            ts = 0
        hours = ts / 3600
        mins = (ts % 3600) / 60
        secs = (ts % 3600) % 60
        tstr = '%02d:%02d' % (mins, secs)
        if int(hours):
            tstr = '%02d:%s' % (hours, tstr)
        return (int(hours), int(mins), int(secs), tstr)

    if not short:
        hours, mins, secs, curr_str = time_tuple(seconds)
        retval = curr_str
        if total:
            hours, mins, secs, total_str = time_tuple(total)
            retval += ' / %s' % total_str
        return retval
    else:
        units = [
            (u'y', 60 * 60 * 24 * 7 * 52),
            (u'w', 60 * 60 * 24 * 7),
            (u'd', 60 * 60 * 24),
            (u'h', 60 * 60),
            (u'm', 60),
            (u's', 1),
        ]

        seconds = int(seconds)

        if seconds < 60:
            return u'   {0:02d}s'.format(seconds)
        for i in xrange(len(units) - 1):
            unit1, limit1 = units[i]
            unit2, limit2 = units[i + 1]
            if seconds >= limit1:
                return u'{0:02d}{1}{2:02d}{3}'.format(
                    seconds // limit1, unit1,
                    (seconds % limit1) // limit2, unit2)
        return u'  ~inf'


def xpathFilter(xpaths):
    '''
    FIXME
    '''
    if isinstance(xpaths, str):
        # "xpath" -> [("xpath", None)] 
        xpaths = [(xpaths, None)]
    elif isinstance(xpaths, tuple) and isinstance(xpaths[0], str):
        # ("xpath", nsmap) -> [("xpath", nsmap)] 
        xpaths = [xpaths]

    def wrapper(func):

        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            from .stanzas import Stanza

            stanza = None
            for a in args:
                if isinstance(a, Stanza):
                    stanza = a
                    break
            if stanza is None:
                raise TypeError("No arguments of type Stanza found")
            for xp in xpaths:
                if isinstance(xp, str):
                    xp, ns_map = xp, None
                else:
                    xp, ns_map = xp

                if stanza.xml.xpath(xp, namespaces=ns_map):
                    # Matching xpath, invoke the function
                    return func(*args, **kwargs)

            # No xpaths match, so the decorated function should not be called.
            @asyncio.coroutine
            def _noOpCoro(*args, **kwargs):
                return None
            return _noOpCoro(*args, **kwargs)

        return wrapped_func

    return wrapper


_dns_cache = {}
@asyncio.coroutine
def resolveHostPort(hostname, port, loop, use_cache=True, client_srv=True,
                    srv_records=None, srv_lookup=True):
    global _dns_cache
    def _chooseSrv(_srvs):
        # TODO: random choices based on prio/weight
        return random.choice(_srvs)

    if use_cache and hostname in _dns_cache:
        cached = _dns_cache[hostname]
        if type(cached) is list:
            # Rechoose a SRV record
            srv_choice = _chooseSrv(cached)
            resolved_srv = yield from resolveHostPort(srv_choice.host,
                                                      srv_choice.port, loop,
                                                      use_cache=True,
                                                      client_srv=client_srv,
                                                      srv_lookup=False)
            return resolved_srv
        else:
            return cached

    resolver = aiodns.DNSResolver(loop=loop)

    ip = None
    try:
        # Given an IP, nothing more to do.
        ip = ip_address(hostname)
        return (str(ip), port)
    except ValueError:
        # Not an IP, move on..,
        pass

    srv_query_type = "_xmpp-client" if client_srv else "_xmpp-server"
    try:
        srv = yield from resolver.query("{}._tcp.{}".format(srv_query_type,
                                                            hostname),
                                        'SRV')
        srv_results = sorted(srv, key=attrgetter("priority", "weight"))

        if srv_records is not None:
            # Copy to callers list
            srv_records += srv_results

        _dns_cache[hostname] = srv_results
        srv_choice = _chooseSrv(srv_results)

        # Reduce to an IP
        if srv_choice.host != hostname:
            resolved_srv = yield from resolveHostPort(srv_choice.host,
                                                      srv_choice.port, loop,
                                                      use_cache=use_cache,
                                                      client_srv=client_srv,
                                                      srv_lookup=False)
            _dns_cache[hostname] = resolved_srv
            return resolved_srv

    except aiodns.error.DNSError:
        # No SRV, moving on...
        pass

    # A record
    arecord = yield from resolver.query(hostname, 'A')

    ip = arecord.pop()
    _dns_cache[hostname] = ip, port
    return ip, port
