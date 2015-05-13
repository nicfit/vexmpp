# -*- coding: utf-8 -*-
import asyncio
import logging

from vexmpp.protocols import muc

from botch.app import APP_NAME
from botch.plugin import Plugin

log = logging.getLogger("botch.plugins.muc")

class MucPlugin(Plugin):
    CONFIG_SECT = "muc"

    @asyncio.coroutine
    def activate(self, bot):
        for jid in [muc.Jid(j.strip())
                      for j in self.config["muc"].get("rooms").split("\n")]:
            # Join rooms
            if not jid.nick:
                jid = muc.Jid("{}/{}".format(jid.bare,  APP_NAME))

            log.info("Joining MUC room {}...".format(jid.full))
            yield from muc.enterRoom(bot, jid.room, jid.host, jid.nick,
                                     timeout=bot.default_timeout)
