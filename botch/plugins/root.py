# -*- coding: utf-8 -*-
import asyncio
import logging

from vexmpp.jid import Jid

from botch.plugin import Plugin

log = logging.getLogger("botch.plugins.root")


class RootPlugin(Plugin):
    CONFIG_SECT = "root"

    @asyncio.coroutine
    def activate(self, bot):
        self.root_jid = Jid(self.config["root"].get("jid")).bare_jid
        log.info("Root user: %s" % self.root_jid)

        sub_msg = "Hi %s, I'm your botch aka %s!" % \
                  (self.root_jid.user.capitalize(), bot.creds.jid.bare)

        root_roster = bot.roster.get(self.root_jid)
        log.info("Root subscription: %s" % root_roster)
        if root_roster and root_roster.subscription == "none":
            root_roster = None

        if not root_roster or root_roster.subscription not in ("to", "both"):
            # Subscribe to root
            resp = yield from iqroster.add(bot, self.root_jid)
            presence.subscribe(bot, self.root_jid, status=welcome_msg)

        while True:
            try:
                stanza = yield from bot.wait(
                            ("/*[contains(@from, '%s')]" % self.root_jid.bare,
                             None),
                            timeout=bot.default_timeout)
                log.verbose("Root task received:\n{}".
                            format(stanza.toXml(pprint=True).decode()))
            except asyncio.TimeoutError:
                pass
