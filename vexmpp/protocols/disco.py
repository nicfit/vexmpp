# -*- coding: utf-8 -*-
import asyncio
from collections import UserDict

from .. import stream
from ..jid import Jid
from ..stanzas import Iq

'''XEP 30'''

NS_URI_BASE  = "http://jabber.org/protocol/disco"
NS_URI_INFO  = "{}#info".format(NS_URI_BASE)
NS_URI_ITEMS = "{}#items".format(NS_URI_BASE)


@asyncio.coroutine
def getInfo(stream, to, node=None, timeout=None):
    iq = Iq(to=to, request=("query", NS_URI_INFO), attrs={"node": node})
    return (yield from stream.sendAndWait(iq, raise_on_error=True,
                                          timeout=timeout))


@asyncio.coroutine
def getItems(stream, to, node=None, timeout=None):
    iq = Iq(to=to, request=("query", NS_URI_ITEMS))
    if node:
        iq._setAttr("node", node)

    iq = yield from stream.sendAndWait(iq, raise_on_error=True, timeout=timeout)
    return iq


class Identity:
    def __init__(self, category, type, name=None, lang=None):
        self.category = category
        self.type = type
        self.name = name
        self.lang = lang

    def __str__(self):
        return ("Identity [category=%s type=%s name=%s lang=%s]"
                % (self.category, self.type, self.name, self.lang))

    def __hash__(self):
        return self.__str__().__hash__()

    def __eq__(self, o):
        return (type(o) == type(self) and
                o.category == self.category and
                o.type == self.type and
                o.name == self.name and
                o.lang == self.lang)


class Info:
    def __init__(self):
        self.disco_jid = None
        self.identities = set()
        self.features = set()
        self.items = set()
        self.node = None


class DiscoCache:
    def __init__(self):
        self.cache = {}

    def clear(self):
        self.cache.clear()

    def getJidsForFeature(self, feature):
        jids = []
        for disco_jid, disco_info in self.cache.items():
            if feature in disco_info.features:
                jids.append(disco_jid)
        return jids


class DiscoCacheMixin(stream.Mixin):
    def __init__(self):
        self._cache = DiscoCache()
        super().__init__([('disco_cache', self._cache)])

    @asyncio.coroutine
    def postSession(self, stream):
        yield from self.update(stream, stream.jid.host)

    @asyncio.coroutine
    def update(self, stream, disco_jid):
        self._cache.clear()

        # Fetch all disco info for the server
        disco_info = yield from self._disco(stream, disco_jid, True)

        # Fetch details about all the server's items (but not info about each
        # item)
        if disco_info and disco_info.items is not None:
            for jid in disco_info.items:
                yield from self._disco(stream, jid, False)

    @asyncio.coroutine
    def _disco(self, stream, jid, fetch_items):
        if not isinstance(jid, Jid):
            jid = Jid(jid)

        disco_info = Info()
        disco_info.disco_jid = jid

        info = yield from getInfo(stream, to=jid,
                                  timeout=stream.default_timeout)

        for child in info.query:
            if child.tag == "{%s}identity" % NS_URI_INFO:
                ident = Identity(category=child.attrib['category'],
                                 type=child.attrib['type'],
                                 name=child.attrib.get('name', None))
                disco_info.identities.add(ident)
            elif child.tag == "{%s}feature" % NS_URI_INFO:
                disco_info.features.add(child.attrib['var'])

        if fetch_items:
            items = yield from getItems(stream, jid,
                                        timeout=stream.default_timeout)

            for child in items.query:
                if child.tag == "{%s}item" % NS_URI_ITEMS:
                    disco_info.items.add(Jid(child.attrib['jid']))

        self._cache.cache[jid] = disco_info
        return disco_info
