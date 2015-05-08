# -*- coding: utf-8 -*-
import asyncio
from ..errors import XmppError
from ..stanzas import Stanza


NS_URI = "urn:ietf:params:xml:ns:xmpp-tls"


@asyncio.coroutine
def handle(stream, feature_elem, timeout=None):
    nsmap = {"tls": NS_URI}

    required = isRequired(feature_elem)

    stream.send(Stanza("starttls", nsmap={None: NS_URI}))
    resp = yield from stream.wait([("/tls:proceed", nsmap),
                                   ("/tls:failure", nsmap)], timeout=timeout)
    if resp.name == "{%s}proceed" % NS_URI:
        yield from stream._transport.starttls()
    else:
        # A real stanza/stream error type is not wrapped by the <failure/>,
        # unlike other newer protocols, so gin up a dummy.
        raise XmppError("starttls failure: %s" % resp.toXml().decode())

    return True


def isRequired(feature_elem):
    return ("{%s}required" % NS_URI) in [c.tag for c in feature_elem]

