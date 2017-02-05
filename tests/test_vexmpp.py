# -*- coding: utf-8 -*-
import vexmpp
"""
test_vexmpp
----------------------------------

Tests for `vexmpp` module.
"""


def test_metadata():
    assert vexmpp.version
    assert vexmpp.__about__.__license__
    assert vexmpp.__about__.__project_name__
    assert vexmpp.__about__.__author__
    assert vexmpp.__about__.__author_email__
    assert vexmpp.__about__.__version__
    assert vexmpp.__about__.__version_info__
    assert vexmpp.__about__.__release__
    assert vexmpp.__about__.__version_txt__
