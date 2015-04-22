#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import asyncio
import logging
import configparser

from vexmpp.jid import Jid
from vexmpp.utils import ArgumentParser, xpathFilter
from vexmpp.application import Application
from vexmpp.client import openConnection, Credentials, ClientStreamCallbacks
from vexmpp.log import DEFAULT_LOGGING_CONFIG
from vexmpp.stanzas import Presence, Message
from vexmpp.protocols import iqroster, presence, muc
from vexmpp import stream

CONFIG_SECT = "botch"
# FIXME
EXAMPLE_CONFIG = """
[%s]
jid = bot@example.com
password = password

%s
""" % (CONFIG_SECT, DEFAULT_LOGGING_CONFIG)


class BotchApp(Application):
    def __init__(self):
        super().__init__(app_name="botch")

        self.arg_parser = ArgumentParser(
                description="Personal XMPP bot.",
                config_opts=ArgumentParser.ConfigOpt.argument,
                config_required=True,
                sample_config=EXAMPLE_CONFIG)

    def run(self):
        self.args = self.arg_parser.parse_args()
        self.config = self.args.config_obj
        return super().run()

    @asyncio.coroutine
    def _initBot(self):
        mixins = [SubscriptionMixin(self.root_jid),
                  iqroster.RosterMixin(),
                 ]
        bot = yield from openConnection(
                Credentials(self.config.get(CONFIG_SECT, "jid"),
                            self.config.get(CONFIG_SECT, "password")),
                callbacks=Callbacks(self), mixins=mixins,
                timeout=30)

        self.log.info("Connected")

        bot.send(Presence())
        self.log.info("Alive!")

        return bot

    @asyncio.coroutine
    def _main(self):
        self.log.info("Botch bot starting...")
        try:
            self.root_jid = Jid(self.config.get(CONFIG_SECT, "root")).bare_jid
            self.bot = yield from self._initBot()

            tasks = [asyncio.async(self._reactorTask()),
                     asyncio.async(self._rootTask()),
                     asyncio.async(self._mucTask()),
                    ]
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
        except Exception as ex:
            self.log.exception(ex)
            return 666

        return 0

    @asyncio.coroutine
    def _mucTask(self):
        # FIXME: error submitting default room config.. and XCP bug where that
        # error does not return the iq id attrib
        #x = yield from muc.enterRoom(self.bot, "foo",
        #                             "conference.jabber.nicfit.net", "vexmpp")
        x = yield from muc.enterRoom(self.bot, "asylum",
                                     "conference.jabber.nicfit.net", "vexmpp")

    @asyncio.coroutine
    def _reactorTask(self):
        self.log.debug("_reactorTask")

        while True:
            stanza = yield from self.bot.wait(("/*", None), timeout=None)
            self.log.verbose(stanza.toXml())

    @asyncio.coroutine
    def _rootTask(self):
        self.log.info("Root user: %s" % self.root_jid.bare)
        sub_msg = "Hi %s, I'm your botch aka %s!" % \
                  (self.root_jid.user.capitalize(), self.bot.creds.jid.bare)

        root_roster = self.bot.roster.get(self.root_jid)
        self.log.info("Root subscription: %s" % root_roster)
        if root_roster and root_roster.subscription == "none":
            root_roster = None

        if not root_roster or root_roster.subscription not in ("to", "both"):
            # Subscribe to root
            resp = yield from iqroster.add(self.bot, self.root_jid)
            presence.subscribe(self.bot, self.root_jid, status=welcome_msg)

        while True:
            stanza = yield from self.bot.wait(
                        ("/*[contains(@from, '%s')]" % self.root_jid.bare,
                         None),
                        timeout=None)
            print("ROOT!\n" + stanza.toXml().decode())


class Callbacks(ClientStreamCallbacks):
    def __init__(self, app):
        self.app = app
    def disconnected(self, stream, reason):
        # TODO Reconnect
        self.app.event_loop.stop()


class SubscriptionMixin(stream.Mixin):
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



app = BotchApp()
sys.exit(app.run())
