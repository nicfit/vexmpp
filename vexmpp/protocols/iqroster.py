# -*- coding: utf-8 -*-
"""
APIs for dealing with Jabber rosters; ``jabber:iq:roster``
http://xmpp.org/rfcs/rfc6121.html#roster
"""
from lxml import etree
from ..stanzas import Iq
from ..stream import Mixin
from ..jid import Jid, internJid
from ..utils import xpathFilter

NS_URI = "jabber:iq:roster"

QUERY_TAG = "{%s}query" % NS_URI
ITEM_TAG = "{%s}item" % NS_URI
GROUP_TAG = "{%s}group" % NS_URI


async def get(stream, timeout=None):
    iq = await stream.sendAndWaitIq(NS_URI, timeout=timeout,
                                    id_prefix="roster_get",
                                    raise_on_error=True)
    return iq


async def add(stream, jid, name=None, groups=None, timeout=None):
    '''Add a new roster item.'''
    iq = Iq(type="set", request=("query", NS_URI), id_prefix="roster_add")
    iq.query.append(RosterItem(jid=jid, name=name, groups=groups).xml)

    iq = await stream.sendAndWait(iq, raise_on_error=True, timeout=timeout)
    return iq


async def update(stream, jid, name=None, groups=None, timeout=None):
    '''Update roster item (same protocol as adding roster items).'''
    return (await add(stream, jid, name=name, groups=groups, timeout=timeout))


async def remove(stream, jid, timeout=None):
    iq = Iq(type="set", request=("query", NS_URI), id_prefix="roster_rem")
    iq.query.append(RosterItem(jid=jid, subscription="remove").xml)

    iq = await stream.sendAndWait(iq, raise_on_error=True, timeout=timeout)
    return iq


class RosterItem(object):
    SUB_NONE = "none"
    SUB_TO = "to"
    SUB_FROM = "from"
    SUB_BOTH = "both"

    ASK_SUBSCRIBE = "subscribe"

    def __init__(self, item_elem=None,
                 jid=None, name=None, subscription=None, groups=None,
                 ask=None):
        if jid and not isinstance(jid, Jid):
            self.jid = Jid(jid).bare_jid
        elif isinstance(jid, Jid):
            self.jid = jid.bare_jid
        elif jid is None:
            self.jid = None
        else:
            raise ValueError("Invalid Jid type")

        self.name = name
        self.subscription = subscription
        self.groups = groups or []
        self.ask = ask

        if item_elem is not None:
            self.update(item_elem)

    def __str__(self):
        return ("RosterItem: jid=%s, subscription=%s, name=%s, groups=%s" %
                (self.jid, self.subscription, self.name, self.groups))

    def update(self, item_elem):
        self.jid = internJid(item_elem.get('jid'))

        self.name = item_elem.get('name')
        self.subscription = item_elem.get('subscription')

        self.groups = []
        for elem in item_elem.findall(GROUP_TAG):
            self.groups.append(elem.text)

        self.ask = item_elem.get('ask')

    @property
    def xml(self):
        item = etree.Element(ITEM_TAG)
        item.set("jid", self.jid.bare)
        if self.subscription:
            item.set("subscription", self.subscription)
        if self.name:
            item.set("name", self.name)

        for group in self.groups:
            gelem = etree.Element(GROUP_TAG)
            gelem.text = group
            item.append(gelem)

        return item


class Roster(object):
    def __init__(self, roster_xml=None):
        self._items = {}
        if roster_xml is not None:
            self._initRoster(roster_xml)

    def __len__(self):
        return len(self._items.keys())

    def __contains__(self, rhs):
        return bool(self.get(rhs) is not None)

    def _initRoster(self, roster_elem):
        query = roster_elem.find(QUERY_TAG)
        for item in query.findall(ITEM_TAG):
            jid = Jid(item.get('jid')).bare_jid
            self._items[jid] = RosterItem(item)

    def updateRoster(self, roster_push):
        if roster_push.request is not None:
            for item_elem in roster_push.request.findall(ITEM_TAG):
                # Running thru get handles normalization.
                current = self.get(item_elem.get('jid'))

                if current and item_elem.get('subscription') == "remove":
                    del self._items[current.jid]
                elif current:
                    self._items[current.jid].update(item_elem)
                else:
                    roster_item = RosterItem(item_elem)
                    self._items[roster_item.jid] = roster_item

    def items(self):
        return list(self._items.values())

    def __iter__(self):
        for i in self.items():
            yield i

    def getJids(self):
        return self._items.keys()

    def get(self, jid):
        if not isinstance(jid, Jid):
            jid = internJid(jid)

        try:
            return self._items[jid]
        except KeyError:
            return None


class RosterMixin(Mixin):
    def __init__(self):
        self.roster = Roster()
        super().__init__([('roster', self.roster)])

    async def postSession(self, stream):
        roster = await get(stream, timeout=stream.default_timeout)
        self.roster.updateRoster(roster)

    @xpathFilter([("/iq[@type='set']/ns:query", {"ns": NS_URI})])
    async def onStanza(self, stream, stanza):
        # Roster push
        self.roster.updateRoster(stanza)

        # ACK push
        result = Iq(to=stream.creds.jid, type="result", id=stanza.id)
        stream.send(result)


# vim: set sw=4:
