# -*- coding: utf-8 -*-
from os.path import expandvars, expanduser
import sys
import types
import asyncio
import logging
from pathlib import Path
from functools import wraps
from collections import namedtuple
from argparse import ArgumentParser

log = logging.getLogger(__name__)


Command = namedtuple("Command", "cmd, callback, acl, arg_parser")
CommandCtx = namedtuple("CommandCtx",
                        "cmd, args, from_jid, bot, arg_parser, stanza, acl")
Trigger = namedtuple("Trigger", "callback, regex, search")
TriggerCtx = namedtuple("TriggerCtx", "match, from_jid, stanza, bot")

all_commands = {}
all_triggers = {}


class command:
    '''TODO'''

    def __init__(self, cmd=None, acl="other", arg_parser=None):
        '''If ``cmd`` is None the name of the decorated function is used,
        otherwise a string or list of strings is allowed.'''
        if type(cmd) in (list, tuple):
            cmd = (str(v) for v in cmd)
        elif cmd is not None:
            cmd = [str(cmd)]

        # cmd is either 1) a tuple of strings, or empty 2) None
        self.cmd = cmd
        self.acl = acl

        if arg_parser and not isinstance(arg_parser, ArgsParser):
            raise ValueError("arg_parser argument must a {}.ArgsParser object"
                             .format(__name__))
        self.arg_parser = arg_parser

    def  __call__(self, func):
        global all_commands

        @wraps(func)
        @asyncio.coroutine
        def cmdFunc(ctx):
            if not ctx.bot.aclCheck(ctx.from_jid, ctx.acl):
                # Failed acl check, 403 response
                return "403"

            parsed_args = None

            if ctx.arg_parser:
                ctx.arg_parser.prog = ctx.cmd
                try:
                    parsed_args = ctx.arg_parser.parse_args(ctx.args)
                except ArgsParserExitInfo as ex:
                    return str(ex)

            if parsed_args:
                # Replace raw args with parsed args.
                env_list = [e for e in ctx]
                env_list[1] = parsed_args
                ctx = CommandCtx(*env_list)

            return func(ctx)

        if not self.cmd:
            self.cmd = [func.__qualname__]

        for cmd in self.cmd:
            if cmd in all_commands:
                log.warn("'{}' clashes with an existing command, ignorning"
                         .format(cmd))
            all_commands[cmd] = Command(cmd, cmdFunc, self.acl, self.arg_parser)

        return cmdFunc


class trigger:
    '''TODO'''

    def __init__(self, regex, search=False):
        self.regex = regex
        self.search = search

    def  __call__(self, func):
        global all_triggers

        @wraps(func)
        @asyncio.coroutine
        def trfunc(*a, **kw):
            return func(*a, **kw)

        name = func.__qualname__
        if name in all_triggers:
            log.warn("'{}' clashes with an existing trigger, ignoring"
                     .format(name))
        all_triggers[name] = Trigger(trfunc, self.regex, self.search)

        return trfunc


class Plugin:
    CONFIG_SECT = None

    def __init__(self, config):
        self.config = config

    @asyncio.coroutine
    def activate(self, stream):
        pass


def loader(path, *paths):
    all_paths = [path] + list(paths)
    all_plugins = []

    for path in (Path(expandvars(expanduser(str(p)))) for p in all_paths):

        if path.is_dir():
            for pyfile in path.glob("*.py"):
                if pyfile.name.startswith("_") == False:
                    new_plugins = _loadMod(pyfile)
                    all_plugins += new_plugins
        else:
            log.warn("Skipping invalid plugin path: {}".format(path))
            continue

    return all_plugins


class ArgsParserExitInfo(Exception):
    def __init__(self, message, is_error=False):
        super().__init__(message)
        self.is_error = is_error


class ArgsParser(ArgumentParser):
    _msg_buffer = []

    def exit(self, status=0, message=None):
        msg = message or "\n".join(self._msg_buffer)
        self._msg_buffer = []
        raise ArgsParserExitInfo("\n" + msg)

    def error(self, message):
        raise ArgsParserExitInfo('\n{usage}\n{prog}: error: {message}\n'
                                 .format(usage=self.format_usage(),
                                         prog=self.prog, message=message))

    def _print_message(self, message, file=None):
        if message:
            self._msg_buffer.append(message)


def _loadMod(pymod):
    plugin_classes = []

    try:
        sys.path.append(str(pymod.parent))
        mod = __import__(pymod.stem, globals=globals(), locals=locals())
    except Exception:
        log.exception("Plugin import error")
        return []
    finally:
        sys.path.remove(str(pymod.parent))

    for sym in dir(mod):
        attr = getattr(mod, sym)
        if ((type(attr) is type) and (attr is not Plugin) and
                issubclass(attr, Plugin)):
            log.info("Loaded plugin '{}' ({})".format(sym, str(pymod)))
            plugin_classes.append(attr)

    return plugin_classes
