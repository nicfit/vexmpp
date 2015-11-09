# -*- coding: utf-8 -*-

"""
test_vexmpp
----------------------------------

Tests for `vexmpp` module.
"""

import unittest

import vexmpp


class TestVexmpp(unittest.TestCase):

    def setUp(self):
        pass

    def test_metadata(self):
        assert(vexmpp.__name__)
        assert(vexmpp.__author__)
        assert(vexmpp.__author_email__)
        assert(vexmpp.__version__)
        assert(vexmpp.__version_info__)
        assert(vexmpp.__release__)
        assert(vexmpp.__license__)
        assert(vexmpp.__version_txt__)

    def test_log(self):
        from vexmpp.log import Logger

        main_log = None
        try:
            main_log = getattr(vexmpp.log, "log")
        except:
            pass
        assert(main_log is not None)
        assert(isinstance(main_log, Logger))

    def tearDown(self):
        pass

    def test_000_something(self):
        pass


if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
