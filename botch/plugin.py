# -*- coding: utf-8 -*-
import sys
import asyncio
import logging
from pathlib import Path
from collections import namedtuple

log = logging.getLogger(__name__)


Command = namedtuple("Command", "cmd, callback, acl")

class Plugin:
    CONFIG_SECT = None

    def __init__(self, config):
        self.config = config
        self._cmds = {}

    @asyncio.coroutine
    def activate(self, stream):
        pass

    def commands(self):
        return dict(self._cmds)

    def addCommand(self, cmd_str, cmd_callable, acl=None):
        if cmd_str in self._cmds:
            log.warn("'{}' clashes with an existing command, ignorning"
                     .format(cmd_str))
        else:
            self._cmds[cmd_str] = Command(cmd_str, cmd_callable, acl)


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

