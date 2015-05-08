# -*- coding: utf-8 -*-
import asyncio
from ..protocols import resourcebind, sessionbind


@asyncio.coroutine
def handle(stream, feature_elem, timeout=None):
    jid = yield from resourcebind.bind(stream, stream.creds.jid.resource,
                                       timeout=timeout)
    if jid.resource != stream.creds.jid.resource:
        # Server generated the resource (or changed it!)
        stream.creds.jid = jid

    # The 'session' feature is in 3921 but NOT 6120
    if feature_elem.getparent().xpath("child::sess:session",
                                      namespaces={"sess":
                                                  sessionbind.NS_URI}):
        # FIXME: only do this if session is in the features
        # Start the session
        yield from sessionbind.newsession(stream, timeout=timeout)
