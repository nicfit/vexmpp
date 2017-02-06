# -*- coding: utf-8 -*-
import asyncio
from operator import itemgetter
from ..stream import Mixin
from ..stanzas import Presence
from ..utils import xpathFilter
from .muc import NS_URI_USER as MUC_USER_NS

PRES_SUB_XPATH = "/presence[@type='subscribe']"
PRES_SUBED_XPATH = "/presence[@type='subscribed']"
PRES_UNSUB_XPATH = "/presence[@type='unsubscribe']"
PRES_UNSUBED_XPATH = "/presence[@type='unsubscribed']"

S10N_XPATHS = [(PRES_SUB_XPATH, None),
               (PRES_SUBED_XPATH, None),
               (PRES_UNSUB_XPATH, None),
               (PRES_UNSUBED_XPATH, None)]


class SubscriptionAckMixin(Mixin):
    '''
    A stream Mixin which acknowledges subscribe and unsubscribe presence
    request.  By default this class will accept all four subscription types.
    '''

    @xpathFilter(S10N_XPATHS)
    async def onStanza(self, stream, stanza):
        if stanza.xml.xpath(PRES_SUB_XPATH):
            stream.send(Presence(to=stanza.frm,
                                 type=Presence.TYPE_SUBSCRIBED))
        elif stanza.xml.xpath(PRES_UNSUB_XPATH):
            stream.send(Presence(to=stanza.frm,
                                 type=Presence.TYPE_UNSUBSCRIBED))
        elif stanza.xml.xpath(PRES_SUBED_XPATH):
            stream.send(Presence(to=stanza.frm,
                                 type=Presence.TYPE_SUBSCRIBE))
        elif stanza.xml.xpath(PRES_UNSUBED_XPATH):
            stream.send(Presence(to=stanza.frm,
                                 type=Presence.TYPE_UNSUBSCRIBE))


class DenySubscriptionAckMixin(Mixin):
    '''
    A stream Mixin which acknowledges subscribe and unsubscribe presence
    stanzas. By default this class will deny all four subscription types.
    '''

    @xpathFilter(S10N_XPATHS)
    async def onStanza(self, stream, stanza):
        if stanza.xml.xpath(PRES_SUB_XPATH):
            stream.send(Presence(to=stanza.frm,
                                 type=Presence.TYPE_UNSUBSCRIBED))
        elif stanza.xml.xpath(PRES_UNSUB_XPATH):
            stream.send(Presence(to=stanza.frm,
                                 type=Presence.TYPE_SUBSCRIBED))
        elif stanza.xml.xpath(PRES_SUBED_XPATH):
            stream.send(Presence(to=stanza.frm,
                                 type=Presence.TYPE_UNSUBSCRIBE))
        elif stanza.xml.xpath(PRES_UNSUBED_XPATH):
            stream.send(Presence(to=stanza.frm,
                                 type=Presence.TYPE_SUBSCRIBE))


def subscribe(stream, jid, status=None):
    stream.send(Presence(to=jid, type=Presence.TYPE_SUBSCRIBE, status=status))


def unsubscribe(stream, jid):
    stream.send(Presence(to=jid, type=Presence.TYPE_UNSUBSCRIBE))


def authorize(stream, jid):
    stream.send(Presence(to=jid, type=Presence.TYPE_SUBSCRIBED))


def subscribed(stream, jid):
    stream.send(Presence(to=jid, type=Presence.TYPE_SUBSCRIBED))


def deauthorize(stream, jid):
    stream.send(Presence(to=jid, type=Presence.TYPE_UNSUBSCRIBED))


def unsubscribed(stream, jid):
    stream.send(Presence(to=jid, type=Presence.TYPE_UNSUBSCRIBED))


class PresenceDict(dict):
    '''
    A dictionary that must maintain the form:
    {bare-jid: {resource1: presence,
                resource2: presence}}

    That is a contacts bare JID with the value being another dictionary
    containing the last seen presence stanza for each resource.
    '''
    def __init__(self):
        dict.__init__(self)

    def iterpres(self, jid, highest_to_lowest=True):
        jid_key = jid.bare

        # Sorting in the Prensence stanza which uses priority and show.
        jid_pres = sorted([(r, p) for r, p in self[jid_key].items()],
                          key=itemgetter(1))
        for r, p in (reversed(jid_pres) if highest_to_lowest else jid_pres):
            yield r, p


class PresenceCacheMixin(Mixin, PresenceDict):
    '''Mixin and cache (i.e. PresenceDict) for user (non multi-user-chat)
    presence.'''

    def __init__(self):
        PresenceDict.__init__(self)
        Mixin.__init__(self, [('presence_cache', self)])
        self._presence_update_event = DataEvent()
        self._self_presence = None

    async def waitForUpdate(self, timeout=None):
        pres = await asyncio.wait_for(self._presence_update.wait(),
                                      timeout=timeout)
        return pres

    @xpathFilter("/presence")
    async def onStanza(self, stream, presence):

        if (presence.type not in [Presence.TYPE_AVAILABLE,
                                  Presence.TYPE_UNAVAILABLE] or
                presence.xml.xpath("//ns:x", namespaces={"ns": MUC_USER_NS})):
            return

        from_jid = presence.frm
        # Presence from a service, not tracking these
        if not from_jid.resource:
            return

        # Update presence cache
        if from_jid.bare not in self:
            resources = {}
            self[from_jid.bare] = resources
        else:
            resources = self[from_jid.bare]

        updated_stanza = None

        if presence.type != Presence.TYPE_UNAVAILABLE:
            # Add/update resource
            resources[from_jid.resource] = presence
            updated_stanza = presence
        elif from_jid.resource in resources:
            # Unavailable, remove
            del resources[from_jid.resource]
            if len(resources.keys()) == 0:
                del self[from_jid.bare]
            updated_stanza = presence

        if updated_stanza:
            self._presence_update_event.set(presence)
            self._presence_update_event.clear()

        if from_jid == stream.jid:
            self._self_presence = presence

        return presence

    @property
    def self(self):
        return self._self_presence


# FIXME: move me
class DataEvent(asyncio.Event):
    def __init__(self, *, loop=None):
        super().__init__(loop=loop)
        self._data = None

    def set(self, payload):
        self._data = payload
        super().set()

    def clear(self):
        self._data = None
        super().clear()

    async def wait(self):
        await super().wait()
        return self._data
