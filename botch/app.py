# -*- coding: utf-8 -*-
import asyncio
import logging
import configparser
from pathlib import Path

from vexmpp.jid import Jid
from vexmpp.stanzas import Message
from vexmpp.application import Application
from vexmpp.log import DEFAULT_LOGGING_CONFIG
from vexmpp.utils import ArgumentParser
from vexmpp.client import Credentials, ClientStreamCallbacks, ClientStream
from . import plugin
from . import reactor

log = logging.getLogger(__name__)
APP_NAME = "botch"
DEFAULT_CONFIG = "~/.botch/config.ini"
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
    _acls = {}

    def _aclInit(self, config):
        self._acls = {}

        for g in ACL_GROUPS:
            if g == "other":
                continue

            jids = [Jid(j) for j in config.get(g, fallback="")
                                          .split("\n") if j]
            self._acls[g] = jids

    def _aclSave(self, config):
        for g in self._acls:
            jids = self._acls[g]
            config[g] = "\n".join([j.bare for j in jids])

    def acl(self, jid):
        if not isinstance(jid, Jid):
            raise ValueError("Jid type required")

        group = None
        for g in self._acls:
            if jid.bare_jid in self._acls[g]:
                group = g
                break

        return group or "other"

    def aclCheck(self, jid, acl):
        jid_acl = self.acl(jid)
        real_jid = jid

        if jid_acl == "other":
            # Check real jids amongst MUC Jids
            room_jid = jid.bare_jid
            nick = jid.resource

            if (room_jid in self.muc_rooms and
                    nick in self.muc_rooms[room_jid].roster):
                item = self.muc_rooms[room_jid].roster[nick]
                if item.jid:
                    jid_acl = self.acl(item.jid)
                    real_jid = item.jid

        authz = bool(ACL_GROUPS.index(jid_acl) <= ACL_GROUPS.index(acl))
        jid = jid.full
        real_jid = real_jid.full
        log.info("{acl} ACL check for {jid}{aka} ({jid_acl}): {valid}"
                 .format(valid=authz,
                         aka=" (aka {})".format(real_jid) if real_jid != jid
                                                          else "",
                         **locals()))
        return authz

    def aclJids(self, acl):
        return [j for j in self._acls[acl]]

    def msgOwners(self, msg):
        for j in self.aclJids("owner"):
            self.send(Message(to=j, body=msg))


class Botch(Application):
    def __init__(self):
        argp = ArgumentParser(
                prog=APP_NAME,
                description="Personal XMPP bot.",
                config_opts=ArgumentParser.ConfigOpt.argument,
                config_required=True,
                default_config_file=DEFAULT_CONFIG,
                sample_config=EXAMPLE_CONFIG)
        super().__init__(app_name=APP_NAME, argument_parser=argp)

    @asyncio.coroutine
    def _initBot(self):
        main_config = self.config[CONFIG_SECT]

        bot = yield from BotchStream.connect(
                Credentials(main_config.get("jid"),
                            main_config.get("password")),
                state_callbacks=Callbacks(self),
                timeout=30)

        self.log.info("Connected {}".format(bot.jid.full))
        bot.app = self

        bot._aclInit(main_config)

        bot.sendPresence(
            status=main_config.get("presence_status"),
            show=main_config.get("presence_show"),
            priority=main_config.getint("presence_priorty", fallback=10))

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

        try:
            self.plugins = self._initPlugins()
            self.bot = yield from self._initBot()

            tasks = []
            tasks.append(reactor.Task(self.config, self.bot, self.plugins))

            for plugin in self.plugins.values():
                tasks.append(asyncio.async(plugin.activate(self.bot)))

            for done_task in asyncio.as_completed(tasks):
                try:
                    result = yield from done_task
                except configparser.Error as ex:
                    self.log.error("Configuration error: {}".format(ex))
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


