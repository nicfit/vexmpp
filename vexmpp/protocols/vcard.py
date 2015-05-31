# -*- coding: utf-8 -*-
import asyncio
from ..stanzas import Iq

'''
Vcard

http://xmpp.org/extensions/xep-0054.html
http://xmpp.org/extensions/xep-0153.html
'''

NS_URI = "vcard-temp"


@asyncio.coroutine
def get(stream, to, timeout=None):
    iq = yield from stream.sendAndWaitIq(NS_URI, to=to, child_name="vCard",
                                         raise_on_error=True,
                                         id_prefix="vcard_get",
                                         timeout=timeout)
    # TODO: ensure vCard child
    return iq


@asyncio.coroutine
def set(stream, to, vcard_xml, timeout=None):
    iq = Iq(to=to, type="set", id_prefix="vcard_set")
    iq.append(vcard_xml)
    iq = yield from stream.sendAndWait(iq, raise_on_error=True, timeout=timeout)
    return iq

# TODO: vCard builder 

