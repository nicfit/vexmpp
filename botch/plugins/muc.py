# -*- coding: utf-8 -*-
import random
import asyncio
import logging

from vexmpp.protocols import muc
from vexmpp.protocols.muc import MucJid

from botch.app import APP_NAME
from botch.plugin import Plugin
from botch.plugin import command, ArgsParser, ArgsParserExitInfo

log = logging.getLogger("botch.plugins.muc")


class MucPlugin(Plugin):
    CONFIG_SECT = "muc"

    @asyncio.coroutine
    def activate(self, bot):
        for jid in [MucJid(j.strip())
                      for j in self.config["muc"].get("rooms").split("\n")]:
            # Join rooms
            if not jid.nick:
                jid = MucJid("{}/{}".format(jid.bare,  APP_NAME))

            log.info("Joining MUC room {}...".format(jid.full))
            try:
                yield from muc.enterRoom(bot, jid.room, jid.host, jid.nick,
                                         timeout=bot.default_timeout)
            except:
                log.exception("Error joining MUC room {}".format(jid.full))
                continue
