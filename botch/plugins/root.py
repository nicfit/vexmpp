# -*- coding: utf-8 -*-
import asyncio
import logging

from vexmpp.jid import Jid
from vexmpp.stream import Mixin
from vexmpp.utils import xpathFilter
from vexmpp.protocols import presence

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
