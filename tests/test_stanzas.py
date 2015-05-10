# -*- coding: utf-8 -*-
from nose.tools import *
from vexmpp.stanzas import *

def testPresenceOrdering():
    assert_less(Presence(priority=5), Presence(priority=10))
    assert_less(Presence(priority=0), Presence(priority=1))
    assert_less(Presence(priority=-1), Presence(priority=0))
    assert_less(Presence(priority=-127), Presence(priority=126))

    assert_less(Presence(priority=5, show=Presence.SHOW_CHAT),
                Presence(priority=10))

    assert_greater(Presence(priority=10, show=Presence.SHOW_CHAT),
                   Presence(priority=10, show=Presence.SHOW_AWAY))
    assert_greater(Presence(priority=10, show=Presence.SHOW_CHAT),
                   Presence(priority=10, show=None))
    assert_greater(Presence(priority=10, show=None),
                   Presence(priority=10, show=Presence.SHOW_AWAY))
    assert_greater(Presence(priority=10, show=Presence.SHOW_AWAY),
                   Presence(priority=10, show=Presence.SHOW_XA))
    assert_greater(Presence(priority=10, show=Presence.SHOW_XA),
                   Presence(priority=10, show=Presence.SHOW_DND))

    assert_false(Presence(priority=5) < Presence(priority=5))
    assert_false(Presence(priority=5) > Presence(priority=5))
    assert_false(Presence(priority=10, show=Presence.SHOW_CHAT) <
                 Presence(priority=10, show=Presence.SHOW_CHAT))
    assert_false(Presence(priority=10, show=Presence.SHOW_CHAT) >
                 Presence(priority=10, show=Presence.SHOW_CHAT))
