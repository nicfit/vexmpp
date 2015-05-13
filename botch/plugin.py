# -*- coding: utf-8 -*-
import sys
import asyncio
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class Plugin:
    CONFIG_SECT = None

    def __init__(self, config):
        self.config = config

    @asyncio.coroutine
    def activate(self, stream):
        pass

    def deactivate(self):
        pass


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
        if ((type(attr) is type) and issubclass(attr, Plugin) and
                attr is not Plugin):
            plugin_classes.append(attr)
            log.info("Loaded plugin '{}' ({})".format(sym, str(pymod)))

    return plugin_classes


def loader(path, *paths):
    all_paths = [path] + list(paths)
    all_plugins = []

    for path in (Path(p) for p in all_paths):
        if path.is_dir():
            for pyfile in path.glob("*.py"):
                if pyfile.name.startswith("_") == False:
                    all_plugins += _loadMod(pyfile)
        else:
            log.warn("Skipping invalid plugin path: {}".format(path))
            continue

    return all_plugins

