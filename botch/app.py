# -*- coding: utf-8 -*-
import asyncio
import logging
import configparser
from pathlib import Path

from vexmpp.application import Application
from vexmpp.utils import ArgumentParser, xpathFilter
from vexmpp.log import DEFAULT_LOGGING_CONFIG
from vexmpp.protocols import presence
from vexmpp.stream import Mixin
from vexmpp.client import Credentials, ClientStreamCallbacks, ClientStream

from . import plugin

log = logging.getLogger(__name__)
APP_NAME = "botch"
CONFIG_SECT = APP_NAME
# FIXME
EXAMPLE_CONFIG = """
[%s]
jid = bot@example.com
password = password

%s
""" % (CONFIG_SECT, DEFAULT_LOGGING_CONFIG)


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
        bot = yield from ClientStream.connect(
                Credentials(self.config.get(CONFIG_SECT, "jid"),
                            self.config.get(CONFIG_SECT, "password")),
                callbacks=Callbacks(self),
                timeout=30)

        self.log.info("Connected {}".format(bot.jid.full))

        bot.sendPresence()
        self.log.info("Alive!")

        return bot


    def _initPlugins(self):
        plugin_paths = []
        plugin_paths.append(Path(__file__).parent / "plugins")
        plugin_paths += [p.strip() for p in self.config[CONFIG_SECT]
                                                .get("plugin_paths")
                                                .split("\n")]
        '''
        '''

        plugins = {}
        for PluginClass in plugin.loader(*plugin_paths):
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
            task_args = (self.config, self.bot)
            tasks.append(asyncio.async(self._reactorTask()))

            for plugin in self.plugins.values():
                tasks.append(asyncio.async(plugin.activate(self.bot)))

            for done_task in asyncio.as_completed(tasks):
                try:
                    result = yield from done_task
                except Exception as ex:
                    self.log.exception(ex)
                    # Continue...
                else:
                    self.log.debug("%s task done, result: %s" % (done_task,
                                                                 result))
        except configparser.Error as ex:
            self.arg_parser.error("Config error: %s" % str(ex))

        return 0

    @asyncio.coroutine
    def _reactorTask(self):
        self.log.debug("_reactorTask")
        while True:
            try:
                stanza = yield from self.bot.wait(("/*", None), timeout=60)
                self.log.info(stanza.toXml(pprint=True).decode())
            except asyncio.TimeoutError:
                pass


class Callbacks(ClientStreamCallbacks):
    def __init__(self, app):
        self.app = app
    def disconnected(self, stream, reason):
        # TODO Reconnect
        self.app.event_loop.stop()


# FIXME: unused
class SubscriptionMixin(Mixin):
    '''Honors subscription requests from root_jid, denies all others.'''
    def __init__(self, root_jid):
        super().__init__()
        self.root_jid = root_jid
        self.yes = presence.SubscriptionAckMixin()
        self.no = presence.DenySubscriptionAckMixin()

    @xpathFilter(presence.S10N_XPATHS)
    @asyncio.coroutine
    def onStanza(self, stream, stanza):
        if stanza.frm.bare_jid == self.root_jid.bare:
            yield from self.yes.onStanza(stream, stanza)
        else:
            yield from self.no.onStanza(stream, stanza)
