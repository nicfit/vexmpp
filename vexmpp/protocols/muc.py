# -*- coding: utf-8 -*-
import asyncio
from lxml import etree
from ..jid import Jid as BaseJid
from ..stanzas import Presence, Iq

'''
Multi-user chat (aka XEP 45)
http://xmpp.org/extensions/xep-0045.html
'''

NS_URI = "http://jabber.org/protocol/muc"
NS_URI_ADMIN = "%s#admin"  % NS_URI
NS_URI_OWNER = "%s#owner"  % NS_URI
NS_URI_UNIQUE = "%s#unique" % NS_URI
NS_URI_USER = "%s#user"   % NS_URI
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
