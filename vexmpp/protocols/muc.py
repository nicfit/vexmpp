# -*- coding: utf-8 -*-
import asyncio
from lxml import etree

from .. import stream
from ..utils import xpathFilter
from ..jid import Jid as BaseJid
from ..stanzas import Presence, Iq

'''
Multi-user chat (aka XEP 45)
http://xmpp.org/extensions/xep-0045.html
'''

NS_URI = "http://jabber.org/protocol/muc"
JINC_NS_URI = "http://www.jabber.com/protocol/muc"
NS_URI_ADMIN = "%s#admin"  % NS_URI
NS_URI_OWNER = "%s#owner"  % NS_URI
NS_URI_UNIQUE = "%s#unique" % NS_URI
NS_URI_USER = "%s#user"   % NS_URI
JINC_NS_URI_HISTORY = "%s#history" % JINC_NS_URI
NS_CONFERENCE_URI = "jabber:x:conference"


class Jid(BaseJid):
    @property
    def nick(self):
        return self.resource

    @property
    def room(self):
        return self.user

    @property
    def room_jid(self):
        return self.bare_jid


def selfPresenceXpath(nick_jid):
    '''110, presence for nick_jid.'''
    xpath = "/presence[@from='{}']/mu:x/mu:status[@code='110']"\
            .format(nick_jid.full)
    return (xpath, {"mu": NS_URI_USER})


def errorPresenceXpath(nick_jid):
    '''Error from the room or service.'''
    xpath = "/presence[@from='{}'][@type='error']".format(nick_jid.bare)
    return (xpath, None)


@asyncio.coroutine
def enterRoom(stream, room, service, nick, password=None,
              config_new_room_callback=None, timeout=None):
    nick_jid = Jid((room, service, nick))

    room_jid = nick_jid.room_jid

    pres = Presence(to=nick_jid)

    x = etree.SubElement(pres.xml, "{%s}x" % NS_URI, nsmap={None: NS_URI})
    if password:
        pw = etree.SubElement(x, "password")
        pw.text = password

    stream.send(pres)

    pres = yield from stream.wait([selfPresenceXpath(nick_jid),
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
            x = etree.SubElement(iq.query, "{jabber:x:data}x",
                                 nsmap={None: "jabber:x:data"})
            x.attrib["type"] = "submit"
            yield from stream.sendAndWait(iq, raise_on_error=True,
                                          timeout=timeout)
        else:
            # Configure room
            iq = Iq(to=room_jid, type="get", request=("query", NS_URI_OWNER))
            room_config = yield from stream.sendAndWait(iq, raise_on_error=True,
                                                        timeout=timeout)
            room_config = config_new_room_callback(room_config)
            yield from stream.sendAndWait(room_config, raise_on_error=True,
                                          timeout=timeout)

    return pres


class RosterItem:
    '''A specialiaztion of RosterItem that adds affiliation and role members.'''

    def __init__(self, nickname, item_elem=None):
        self.nickname = nickname
        self.affiliation = None
        self.role = None
        self.jid = None

        if item_elem:
            import ipdb; ipdb.set_trace()
            a = item_elem['affiliation']
            self.affiliation = a if a != 'none' else None
            r = item_elem['role']
            self.role = r if r != 'none' else None
            j = item_elem['jid']
            self.jid = ImmutableJID(j) if j else None

    def __str__(self):
        return ("RosterItem [nickname: {nickname}, jid: {jid}, "
                "affiliation: {affiliation}, role: {role}]"
                .format(nickname=self.nickname,
                        jid=self.jid.full if self.jid else None,
                        affiliation=self.affiliation, role=self.role))


class RoomInfo:
    '''A container for MUC room information including occupant roster.'''

    def __init__(self, room_jid, nick):
        self.jid = Jid(room_jid.full())
        self.nickname = nick
        self.roster = []

    def addToRoster(self, roster_item):
        '''Add/update an occupant roster entry corresponding to roster_item.'''
        self.removeFromRoster(roster_item.nickname)
        self.roster.append(roster_item)

    def removeFromRoster(self, nickname):
        '''Remove an occupant roster entry corresponding to nickname.'''
        for item in self.roster:
            if item.nickname == nickname:
                self.roster.remove(item)
                return item
        return None


##
# \brief This class provides MUC room and presence tracking for a stream.
#
# This Mixin exports the data 'muc_rooms' which is a dictionary of the form:
# \c {room_jid: MucRoomInfo}
#
# \note Due to XCP not supporting status=110 to distinguish the stream's
#       muc presence from other occupant presence the use of
#       jload.xmpp.protocols.muc.enterRoom is required to prepare the state
#       of this Mixin.
class MucMixin(stream.Mixin):
    PRESENCE_IN_XPATH = ("/presence/muc_user:x", {"muc_user": NS_URI_USER})
    PRESENCE_OUT_XPATH = ("/presence/muc:x", {"muc": NS_URI})
    #INVITE_XPATH = ("/message/muc_user:x/invite", {"muc_user": NS_URI_USER})

    def __init__(self):
        self._muc_rooms = {}
        self._muc_rooms_exiting = {}

        super().__init__([('muc_rooms', self._muc_rooms),
                          ('muc_rooms_exiting', self._muc_rooms_exiting)])

    @xpathFilter([PRESENCE_IN_XPATH,
                  PRESENCE_OUT_XPATH])
    @asyncio.coroutine
    def onStanza(self, stream, stanza):
        print("MucMixin: {}".format(stanza.toXml().decode()))

        '''
        if MucMixin.PRESENCE_IN_XPATH.matches(stanza):
            log.debug("MucMixin presence stanza received: %s" % stanza.toXml())
            nick_jid = stanza.getFrom(as_jid=True)
            room_jid = nick_jid.userhostJID()

            # The muc_rooms dictionary is populated in enterRoom.
            # The muc_rooms_exiting dictionary is populated in exitRoom
            if self._muc_rooms.has_key(room_jid):
                room_info = self._muc_rooms[room_jid]
            elif self._muc_rooms_exiting.has_key(room_jid):
                room_info = self._muc_rooms_exiting[room_jid]
            else:
                # We can get unavailable presence when the room is destoyed
                # even after we left it.
                return

            if room_info.nickname == nick_jid.nick or SELFPRESENCE_XQUERY.matches(stanza):
                # This is presence for "me"
                if stanza.getType() != Presence.TYPE_AVAILABLE:
                    # Check for status 303 - nick change.
                    x = stanza.getElement("x", NS_URI_USER)
                    status = x.getElement("status")
                    if (not status or
                            status['code'] != str(STATUS_NICK_CHANGE)):
                        if self._muc_rooms.has_key(room_jid):
                            del self._muc_rooms[room_jid]
                        if self._muc_rooms_exiting.has_key(room_jid):
                            del self._muc_rooms_exiting[room_jid]
                else:
                    x = stanza.getElement("x", NS_URI_USER)
                    roster_item = MucRosterItem(nick_jid.nick, item_elem=x.item)
                    room_info.addToRoster(roster_item)
            else:
                # This is presence for another occupant
                if stanza.getType() != Presence.TYPE_AVAILABLE:
                    room_info.removeFromRoster(nick_jid.nick)
                else:
                    x = stanza.getElement("x", NS_URI_USER)
                    roster_item = MucRosterItem(nick_jid.nick, item_elem=x.item)
                    # This will update instead of add if that required
                    room_info.addToRoster(roster_item)
        elif MucMixin.INVITE_XPATH.matches(stanza):
            log.debug("MucMixin invite message received: %s" %
                       stanza.toXml())
            self._handleInvite(stream, stanza)

        '''
