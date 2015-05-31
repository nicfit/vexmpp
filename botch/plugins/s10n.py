# -*- coding: utf-8 -*-
import asyncio
import logging

from vexmpp.jid import Jid
from vexmpp.stream import Mixin
from vexmpp.utils import xpathFilter
from vexmpp.protocols import presence, iqroster

from botch.plugin import Plugin

log = logging.getLogger("botch.plugins.s10n")


class S10nPlugin(Plugin):
    CONFIG_SECT = "s10n"

    @asyncio.coroutine
    def _subscribe(self, bot, jid):
        sub_msg = "Hello {acl_title} {name} <{jid}>, I'm your botch aka {me}."\
                  .format(acl_title=bot.acl(jid), name=jid.user.capitalize(),
                          jid=jid.full, me=bot.creds.jid.bare)

        try:
            resp = yield from iqroster.add(bot, jid)
            presence.subscribe(bot, jid, status=sub_msg)
        except (asyncio.TimeoutError, XmppError) as ex:
            log.warn("Subscription to {} failed: {}".format(jid.full, ex))

    @asyncio.coroutine
    def activate(self, bot):
        # Replace default subscription mixin with our acl based version
        for mixin in bot._mixins:
            if mixin.__class__ is presence.SubscriptionAckMixin:
                bot._mixins.remove(mixin)
                break
        bot._mixins.append(SubscriptionMixin())

        # Update subscription for the config'd acl groups
        for acl_grp in self.config["s10n"]\
                           .get("subscribe_acls", fallback="").split():
            acl_jids = bot.aclJids(acl_grp)
            for sub_jid in acl_jids:
                curr = bot.roster.get(sub_jid)
                log.debug("Subscription: %s" % curr)

                if curr and curr.subscription == "none":
                    curr = None

                if (not curr or curr.subscription not in ("to", "both")):
                    # Subscribe
                    asyncio.async(self._subscribe(bot, sub_jid))


class SubscriptionMixin(Mixin):
    '''Honors subscription requests from ACL groups in [s10n] subscribe_acls
    configuration, and denies all others.'''
    def __init__(self):
        super().__init__()
        self._yes = presence.SubscriptionAckMixin()
        self._no = presence.DenySubscriptionAckMixin()

    @xpathFilter(presence.S10N_XPATHS)
    @asyncio.coroutine
    def onStanza(self, bot, stanza):
        acl = bot.acl(stanza.frm.bare_jid)
        s10n_acls = bot.app.config["s10n"].get("subscribe_acls", fallback="")\
                                          .split()
        if acl in s10n_acls:
            yield from self._yes.onStanza(bot, stanza)
        else:
            yield from self._no.onStanza(bot, stanza)
