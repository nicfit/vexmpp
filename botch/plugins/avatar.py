# -*- coding: utf-8 -*-
import base64
import asyncio
import logging
import mimetypes

from lxml import etree
from vexmpp.stanzas import Iq
from vexmpp.protocols import vcard
from vexmpp.errors import XmppError

from botch.plugin import Plugin

log = logging.getLogger("botch.plugins.avatar")


class AvatarPlugin(Plugin):
    CONFIG_SECT = "avatar"

    VCARD_PHOTO_XML = '''
    <PHOTO>
      <TYPE>{avatar_mimetype}</TYPE>
      <BINVAL>{avatar_b64}</BINVAL>
    </PHOTO>
    '''

    @asyncio.coroutine
    def activate(self, bot):
        vcard_jid = bot.disco_cache.getJidsForFeature(vcard.NS_URI)
        if not vcard_jid:
            log.warn("Server does support vcards")
            return

        avatar_file = self.config["avatar"].get("img")
        mt, _ = mimetypes.guess_type(avatar_file)
        if not mt:
            log.warn("Invalid avatar_file: {}".format(avatar_file))
            return

        with open(avatar_file, "rb") as fp:
            photo_xml = etree.fromstring(self.VCARD_PHOTO_XML.
                    format(avatar_mimetype=mt,
                           avatar_b64=str(base64.b64encode(fp.read()),
                                          "ascii")))

        try:
            iq = yield from vcard.get(bot, bot.jid.bare,
                                      timeout=bot.default_timeout)


            vc = iq.xml.find("{%s}%s" % (vcard.NS_URI, "vCard"))
            if vc is not None:
                iq.xml.remove(vc)

                photo = vc.find("{%s}%s" % (vcard.NS_URI, "PHOTO"))
                if photo is not None:
                    vc.remove(photo)
                vc.append(photo_xml)

                _ = yield from vcard.set(bot, bot.jid.bare, vc,
                                         timeout=bot.default_timeout)
            else:
                log.warn("Missing vCard in server response")
        except XmppError as ex:
            log.error(str(ex))
