# -*- coding: utf-8 -*-
from .. import stream
from ..utils import xpathFilter
from ..jid import Jid as BaseJid
from ..stanzas import Presence, Iq, ElementWrapper

'''
Multi-user chat (aka XEP 45)
http://xmpp.org/extensions/xep-0045.html
'''

from .. import getLogger
log = getLogger(__name__)

NS_URI = "http://jabber.org/protocol/muc"
JINC_NS_URI = "http://www.jabber.com/protocol/muc"
NS_URI_ADMIN = "%s#admin" % NS_URI
NS_URI_OWNER = "%s#owner" % NS_URI
NS_URI_UNIQUE = "%s#unique" % NS_URI
NS_URI_USER = "%s#user" % NS_URI
JINC_NS_URI_HISTORY = "%s#history" % JINC_NS_URI
NS_CONFERENCE_URI = "jabber:x:conference"


class MucJid(BaseJid):
    @property
    def nick(self):
        return self.resource

    @property
    def room(self):
        return self.user

    @property
    def room_jid(self):
        return MucJid(self.bare_jid)


def selfPresenceXpath(nick_jid):
    '''110, presence for nick_jid.'''
    xpath = "/presence[@from='{}']/mu:x/mu:status[@code='110']"\
            .format(nick_jid.full)
    return (xpath, {"mu": NS_URI_USER})


def errorPresenceXpath(nick_jid):
    '''Error from the room or service.'''
    xpath = "/presence[@from='{}'][@type='error']".format(nick_jid.bare)
    return (xpath, None)


class RosterItem:
    nickname = None
    affiliation = None
    role = None
    jid = None
    self_presence = False

    def __init__(self, nickname, item_elem=None, self_presence=False):
        self.nickname = nickname
        self.self_presence = self_presence

        def _itemGet(item, attr):
            val = item.get(attr)
            if val in (None, "none"):
                val = None
            return val

        if item_elem is not None:
            self.affiliation = _itemGet(item_elem, "affiliation")
            self.role = _itemGet(item_elem, "role")
            jid = _itemGet(item_elem, "jid")
            self.jid = BaseJid(jid) if jid else None

    def __str__(self):
        return ("RosterItem [nickname: {nickname}, jid: {jid}, "
                "affiliation: {affiliation}, role: {role}]"
                .format(nickname=self.nickname,
                        jid=self.jid.full if self.jid else None,
                        affiliation=self.affiliation, role=self.role))


class RoomInfo:
    '''A container for MUC room information including occupant roster.'''

    def __init__(self, room_jid):
        self.jid = room_jid.room_jid  # Making sure to drop any resource/nick
        self._roster = {}

    def addToRoster(self, roster_item):
        '''Add/update an occupant roster entry corresponding to roster_item.'''
        self.removeFromRoster(roster_item.nickname)
        self._roster[roster_item.nickname] = roster_item

    def removeFromRoster(self, nickname):
        '''Remove an occupant roster entry corresponding to nickname.'''
        item = None
        if nickname in self._roster:
            item = self._roster[nickname]
            del self._roster[nickname]
        return item

    @property
    def self_jid(self):
        for r in self._roster.values():
            if r.self_presence:
                return r.self_presence
        raise AssertionError("No self presence JID")

    @property
    def roster(self):
        '''The roster is a dict with nickname keys and RosterItem values.'''
        return dict(self._roster)


class MucMixin(stream.Mixin):
    '''This class provides MUC room and presence tracking for a stream.'''
    PRESENCE_XPATH = ("/presence/muc_user:x", {"muc_user": NS_URI_USER})

    def __init__(self):
        self._muc_rooms = {}
        super().__init__([('muc_rooms', self._muc_rooms)])

    @xpathFilter(PRESENCE_XPATH)
    async def onStanza(self, stream, stanza):
        log.debug("MucMixin: {}".format(stanza.toXml().decode()))

        pres = stanza
        muc_jid = MucJid(pres.frm)
        room_jid = muc_jid.room_jid
        x = pres.x(NS_URI_USER)
        status = x.find("{%s}status" % NS_URI_USER)
        item = x.find("{%s}item" % NS_URI_USER)

        self_presence = None
        if status is not None and (status.get("code") == "110"):
            self_presence = muc_jid

        if room_jid in self._muc_rooms:
            room_info = self._muc_rooms[room_jid]
        else:
            room_info = RoomInfo(muc_jid)
            self._muc_rooms[room_jid] = room_info

        if pres.type == pres.TYPE_AVAILABLE:
            roster_item = RosterItem(muc_jid.nick, item_elem=item,
                                     self_presence=self_presence)
            room_info.addToRoster(roster_item)
        else:
            room_info.removeFromRoster(muc_jid.nick)
            if self_presence:
                del self._muc_rooms[room_jid]


async def enterRoom(stream, room, service, nick, password=None,
                    config_new_room_callback=None, timeout=None):
    nick_jid = MucJid((room, service, nick))

    room_jid = nick_jid.room_jid

    pres = Presence(to=nick_jid)

    x = pres.appendChild("x", NS_URI)
    if password:
        pw = x.appendChild("password")
        pw.text = password

    stream.send(pres)

    pres = await  stream.wait([selfPresenceXpath(nick_jid),
                              errorPresenceXpath(nick_jid)],
                              timeout=timeout)
    if pres.error:
        raise pres.error

    ROOM_CREATED_PRESENCE_XPATH = ("/presence/mu:x/mu:status[@code='201']",
                                   {"mu": NS_URI_USER})
    ROOM_OWNER_PRESENCE_XPATH = \
            ("/presence/mu:x/mu:item[@affiliation='owner']",
             {"mu": NS_URI_USER})

    # Owner create operations
    if (pres.xml.xpath(ROOM_OWNER_PRESENCE_XPATH[0],
                       namespaces=ROOM_OWNER_PRESENCE_XPATH[1]) and
        pres.xml.xpath(ROOM_CREATED_PRESENCE_XPATH[0],
                       namespaces=ROOM_CREATED_PRESENCE_XPATH[1])):

        if config_new_room_callback is None:
            # New instant room, accept the default config
            iq = Iq(to=room_jid, type="set", request=("query", NS_URI_OWNER))
            x = iq.query.appendChild("x", "jabber:x:data")
            x.attrib["type"] = "submit"
            await stream.sendAndWait(iq, raise_on_error=True, timeout=timeout)
        else:
            # Configure room
            iq = Iq(to=room_jid, type="get", request=("query", NS_URI_OWNER))
            room_config = await stream.sendAndWait(iq, raise_on_error=True,
                                                   timeout=timeout)
            room_config = config_new_room_callback(room_config)
            await stream.sendAndWait(room_config, raise_on_error=True,
                                     timeout=timeout)

    return pres


async def kick(stream, nick_jid, reason, timeout=None):
    iq = Iq(to=nick_jid.room_jid, type="set", request=("query", NS_URI_ADMIN))
    query = ElementWrapper(iq.query)
    item = ElementWrapper(query.appendChild("item"))
    item.set("nick", nick_jid.nick)
    item.set("role", "none")
    query.appendChild("reason").text = reason

    await stream.sendAndWait(iq, raise_on_error=True, timeout=timeout)


async def leaveRoom(stream, nick_jid, leave_msg=None, timeout=None):
    pres = Presence(to=nick_jid, type=Presence.TYPE_UNAVAILABLE)
    if leave_msg:
        pres.appendChild("status").text = leave_msg

    stream.send(pres)
    pres = await stream.wait(selfPresenceXpath(nick_jid))
    return pres
