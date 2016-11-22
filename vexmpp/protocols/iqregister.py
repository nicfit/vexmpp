# -*- coding: utf-8 -*-

NS_URI = "jabber:iq:register"


async def getForm(stream):
    iq = await stream.sendAndWaitIq(NS_URI, type="get", raise_on_error=True)
    return iq
