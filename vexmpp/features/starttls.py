# -*- coding: utf-8 -*-
import asyncio
from ..errors import XmppError
from ..stanzas import Stanza


NS_URI = "urn:ietf:params:xml:ns:xmpp-tls"


@asyncio.coroutine
def handle(stream, feature_elem, timeout=None):
    nsmap = {"tls": NS_URI}

    required = ("{%s}required" % NS_URI) in [c.tag for c in feature_elem]

    stream.send(Stanza("starttls", nsmap={None: NS_URI}))
    resp = yield from stream.wait([("/tls:proceed", nsmap),
                                   ("/tls:failure", nsmap)], timeout=timeout)
    if resp.name == "{%s}proceed" % NS_URI:
        yield from stream._transport.starttls()
        return True
    else:
        raise XmppError("starttls failure: %s" % resp.toXml().decode())

    return False


