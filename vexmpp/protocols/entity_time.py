# -*- coding: utf-8 -*-
import time
from lxml import etree

from ..stanzas import Iq
from ..stream import Mixin
from ..utils import xpathFilter

from .. import getLogger
log = getLogger(__name__)

"""
Protocol for XEP 0202 - Entity Time support.
http://www.xmpp.org/extensions/xep-0202.html
"""

NS_URI = "urn:xmpp:time"
GET_XPATH = ("/iq[@type='get']/ns:time", {"ns": NS_URI})


async def get(stream, to):
    iq = await stream.sendAndWaitIq(NS_URI, to=to, child_name="time",
                                    raise_on_error=True)
    return iq


class EntityTimeMixin(Mixin):

    @xpathFilter(GET_XPATH)
    async def onStanza(self, stream, stanza):
        log.debug("%s received" % NS_URI)

        result = Iq(xml=stanza.xml)
        result.swapToFrom()
        result.type = "result"

        elem = etree.Element("tzo")
        timezone = time.timezone if not time.localtime().tm_isdst \
                                 else time.altzone
        timezone = (-1 * timezone) if time.localtime().tm_gmtoff < 0 \
                                   else timezone
        elem.text = "%+03d:%02d" % (timezone / 60, abs(timezone % 60))
        result.request.append(elem)

        elem = etree.Element("utc")
        elem.text = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        result.request.append(elem)

        stream.send(result)
