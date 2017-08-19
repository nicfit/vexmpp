from vexmpp.stanzas import *


def testPresenceOrdering():
    assert Presence(priority=5) < Presence(priority=10)
    assert Presence(priority=0) < Presence(priority=1)
    assert Presence(priority=-1) < Presence(priority=0)
    assert Presence(priority=-127) < Presence(priority=126)
    assert Presence(priority=5,
                    show=Presence.SHOW_CHAT) < Presence(priority=10)

    assert Presence(priority=10,
                    show=Presence.SHOW_CHAT) > Presence(priority=10,
                                                        show=Presence.SHOW_AWAY)
    assert Presence(priority=10, show=Presence.SHOW_CHAT) >\
           Presence(priority=10, show=None)
    assert Presence(priority=10, show=None) >\
           Presence(priority=10, show=Presence.SHOW_AWAY)
    assert Presence(priority=10, show=Presence.SHOW_AWAY) >\
           Presence(priority=10, show=Presence.SHOW_XA)
    assert Presence(priority=10, show=Presence.SHOW_XA) >\
           Presence(priority=10, show=Presence.SHOW_DND)

    assert not (Presence(priority=5) < Presence(priority=5))
    assert not (Presence(priority=5) > Presence(priority=5))
    assert not (Presence(priority=10, show=Presence.SHOW_CHAT) <
                Presence(priority=10, show=Presence.SHOW_CHAT))
    assert not (Presence(priority=10, show=Presence.SHOW_CHAT) >
                Presence(priority=10, show=Presence.SHOW_CHAT))
