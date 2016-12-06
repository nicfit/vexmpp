# -*- coding: utf-8 -*-
from ..stanzas import Iq


NS_URI = "urn:ietf:params:xml:ns:xmpp-session"


async def newsession(stream, timeout=None):
    iq = Iq(type="set", request=("session", NS_URI))
    iq.setId("sess")
    resp = await stream.sendAndWait(iq, timeout=timeout)
    if resp.error:
        # TODO
        raise NotImplementedError
