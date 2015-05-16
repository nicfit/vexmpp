# -*- coding: utf-8 -*-
import asyncio

NS_URI = "jabber:iq:register"


@asyncio.coroutine
def getForm(stream):
    iq = yield from stream.sendAndWaitIq(NS_URI, type="get",
                                         raise_on_error=True)
    return iq
