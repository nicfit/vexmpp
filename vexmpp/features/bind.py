# -*- coding: utf-8 -*-
from ..protocols import resourcebind, sessionbind


async def handle(stream, feature_elem, timeout=None):
    jid = await resourcebind.bind(stream, stream.creds.jid.resource,
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
        await sessionbind.newsession(stream, timeout=timeout)
