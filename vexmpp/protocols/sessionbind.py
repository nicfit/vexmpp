# -*- coding: utf-8 -*-
import asyncio
from ..stanzas import Iq


NS_URI = "urn:ietf:params:xml:ns:xmpp-session"


@asyncio.coroutine
def newsession(stream, timeout=None):
    iq = Iq(type="set", request=("session", NS_URI))
    iq.setId("sess")
    resp = yield from stream.sendAndWait(iq, timeout=timeout)
    if resp.error:
        # TODO
        raise NotImplementedError
