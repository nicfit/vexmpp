# -*- coding: utf-8 -*-
import asyncio
import logging
import configparser
from pathlib import Path

from vexmpp.jid import Jid
from vexmpp.application import Application
from vexmpp.log import DEFAULT_LOGGING_CONFIG
from vexmpp.utils import ArgumentParser
from vexmpp.client import Credentials, ClientStreamCallbacks, ClientStream
from . import plugin
from . import reactor

log = logging.getLogger(__name__)
APP_NAME = "botch"
CONFIG_SECT = APP_NAME
# FIXME
EXAMPLE_CONFIG = """
[%s]
jid = bot@example.com
password = password
#plugin_paths = path1
#               path2

%s
""" % (CONFIG_SECT, DEFAULT_LOGGING_CONFIG)

ACL_GROUPS = ("owner", "admin", "friend", "other", "blocked", "enemy")


class BotchStream(ClientStream):
    _acl = {}

    def acl(self, jid):
        if not isinstance(jid, Jid):
            raise ValueError("Jid type required")

        group = None
        for g in self._acl:
            if jid.bare_jid in self._acl[g]:
                group = g
                break

        return group or "other"

    def aclCheck(self, jid, acl):
        jid_acl = self.acl(jid)
        return ACL_GROUPS.index(jid_acl) <= ACL_GROUPS.index(acl)


class Botch(Application):
    def __init__(self):
        argp = ArgumentParser(
                prog=APP_NAME,
                description="Personal XMPP bot.",
                config_opts=ArgumentParser.ConfigOpt.argument,
                config_required=True,
                sample_config=EXAMPLE_CONFIG)
        super().__init__(app_name=APP_NAME, argument_parser=argp)

    @asyncio.coroutine
    def _initBot(self):
        bot = yield from BotchStream.connect(
                Credentials(self.config.get(CONFIG_SECT, "jid"),
                            self.config.get(CONFIG_SECT, "password")),
                state_callbacks=Callbacks(self),
                timeout=30)

        self.log.info("Connected {}".format(bot.jid.full))
        bot.app = self

        for g in ACL_GROUPS:
            if g == "other":
                continue

            jids = [Jid(j) for j in self.config.get(CONFIG_SECT, g,
                                                    fallback="")
                                                .split("\n") if j]
            bot._acl[g] = jids

        bot.sendPresence()
        self.log.info("Alive!")

        return bot


    def _initPlugins(self):
        plugin_paths = []
        plugin_paths.append(Path(__file__).parent / "plugins")
        if "plugin_paths" in self.config[CONFIG_SECT]:
            plugin_paths += [p.strip() for p in self.config[CONFIG_SECT]
                                                    .get("plugin_paths")
                                                    .split("\n")]

        plugins = {}
        for PluginClass in plugin.loader(*plugin_paths):
            if (PluginClass.CONFIG_SECT and
                    PluginClass.CONFIG_SECT not in self.config):
                log.info("'{}' disabled, no [{}] config"
                         .format(PluginClass.__name__, PluginClass.CONFIG_SECT))
                continue

            try:
                p = PluginClass(self.config)
            except:
                log.exception("Plugin construct error")
            else:
                plugins[PluginClass] = p
        return plugins

    @asyncio.coroutine
    def _main(self):
        self.log.info("Botch bot starting...")
        self.config = self.args.config_obj

        '''
        import signal
        def _interrupted(signum):
            log.info("Interrupted {}".format(signum))
            self.stop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.event_loop.add_signal_handler(sig, _interrupted, sig)
        '''

        try:
            self.plugins = self._initPlugins()
            self.bot = yield from self._initBot()

            #import ipdb; ipdb.set_trace()

            tasks = []
            tasks.append(reactor.Task(self.config, self.bot, self.plugins))

            for plugin in self.plugins.values():
                tasks.append(asyncio.async(plugin.activate(self.bot)))

            for done_task in asyncio.as_completed(tasks):
                try:
                    result = yield from done_task
                except asyncio.CancelledError:
                    return self._exit_status
                except Exception as ex:
                    self.log.exception(ex)
                    # Continue...
                else:
                    self.log.debug("%s task done, result: %s" % (done_task,
                                                                 result))
        except configparser.Error as ex:
            self.arg_parser.error("Config error: %s" % str(ex))

        return 0


class Callbacks(ClientStreamCallbacks):
    def __init__(self, app):
        self.app = app
    def disconnected(self, stream, reason):
        # TODO Reconnect
        self.app.stop()


