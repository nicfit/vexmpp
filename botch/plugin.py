# -*- coding: utf-8 -*-
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
CommandEnv = namedtuple("CommandEnv", "cmd, args, from_jid, bot, arg_parser")

all_commands = {}


class Plugin:
    CONFIG_SECT = None

    def __init__(self, config):
        self.config = config

    @asyncio.coroutine
    def activate(self, stream):
        pass


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
        def cmdFunc(cmd_env):
            parsed_args = None

            if cmd_env.arg_parser:
                cmd_env.arg_parser.prog = cmd_env.cmd
                try:
                    parsed_args = cmd_env.arg_parser.parse_args(cmd_env.args)
                except ArgsParserExitInfo as ex:
                    return str(ex)

            if parsed_args:
                # Replace raw args with parsed args.
                env_list = [e for e in cmd_env]
                env_list[1] = parsed_args
                cmd_env = CommandEnv(*env_list)

            return func(cmd_env)

        if not self.cmd:
            self.cmd = [func.__qualname__]

        for cmd in self.cmd:
            if cmd in all_commands:
                log.warn("'{}' clashes with an existing command, ignorning"
                         .format(cmd))
            all_commands[cmd] = Command(cmd, cmdFunc, self.acl, self.arg_parser)

        return cmdFunc


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


def loader(path, *paths):
    all_paths = [path] + list(paths)
    all_plugins = []

    for path in (Path(p) for p in all_paths):
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
