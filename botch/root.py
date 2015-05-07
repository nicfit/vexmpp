# -*- coding: utf-8 -*-
import asyncio
import logging

from vexmpp.jid import Jid

log = logging.getLogger(__name__)


@asyncio.coroutine
def task(config, bot):
    root_jid = Jid(config["root"].get("jid")).bare_jid

    log.info("Root user: %s" % root_jid)
    sub_msg = "Hi %s, I'm your botch aka %s!" % \
              (root_jid.user.capitalize(), bot.creds.jid.bare)

    root_roster = bot.roster.get(root_jid)
    log.info("Root subscription: %s" % root_roster)
    if root_roster and root_roster.subscription == "none":
        root_roster = None

    if not root_roster or root_roster.subscription not in ("to", "both"):
        # Subscribe to root
        resp = yield from iqroster.add(bot, root_jid)
        presence.subscribe(bot, root_jid, status=welcome_msg)

    while True:
        try:
            stanza = yield from bot.wait(
                        ("/*[contains(@from, '%s')]" % root_jid.bare,
                         None),
                        timeout=bot.default_timeout)
            print("ROOT!\n" + stanza.toXml().decode())
        except asyncio.TimeoutError:
            pass
