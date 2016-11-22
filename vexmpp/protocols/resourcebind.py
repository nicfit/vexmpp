# -*- coding: utf-8 -*-
from lxml import etree
from ..jid import Jid
from ..stanzas import Iq

from ..log import getLogger
log = getLogger(__name__)

NS_URI = "urn:ietf:params:xml:ns:xmpp-bind"


async def bind(stream, resource, timeout=None):
    iq = Iq(type="set", request=("bind", NS_URI))
    iq.setId("bind")

    if resource:
        resource_elem = etree.Element("resource")
        resource_elem.text = resource
        iq.request.append(resource_elem)

    resp = await stream.sendAndWait(iq, timeout=timeout)
    if resp.error:
        raise resp.error

    # Get the jid out of the response.
    jid = resp.request.findtext("bind:jid", namespaces={"bind": NS_URI})
    if not jid:
        log.error("Resource bind result did not contain a 'jid'")
        return None

    return Jid(jid)
