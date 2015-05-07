# -*- coding: utf-8 -*-
import asyncio
import logging

from vexmpp.protocols import muc

log = logging.getLogger(__name__)


@asyncio.coroutine
def task(config, bot):

    for jid in [muc.Jid(j) for j in config["muc"].get("rooms").split()]:
        # Join rooms
        if not jid.nick:
            jid = muc.Jid("{}/{}".format(jid.bare,  "botch"))
        log.info("Joining MUC room {}...".format(jid.full))
        yield from muc.enterRoom(bot, jid.room, jid.host, jid.nick,
                                 timeout=bot.default_timeout)
