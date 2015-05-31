# -*- coding: utf-8 -*-

"""
test_jid
----------------------------------

Tests for `vexmpp.xmpp.jid` module.
"""
import unittest
from vexmpp.jid import Jid, _parse, _prep, InvalidJidError, internJid


class TestJidParsing(unittest.TestCase):

    def setUp(self):
        pass

    def test_basic(self):
        self.assertEqual(_parse("user@host/resource"),
                          ("user", "host", "resource"))
        self.assertEqual(_parse("user@host"),
                          ("user", "host", None))
        self.assertEqual(_parse("host"),
                          (None, "host", None))
        self.assertEqual(_parse("host/resource"),
                          (None, "host", "resource"))

        self.assertEqual(_parse("foo/bar@baz"),
                          (None, "foo", "bar@baz"))
        self.assertEqual(_parse("boo@foo/bar@baz"),
                          ("boo", "foo", "bar@baz"))
        self.assertEqual(_parse("boo@foo/bar/baz"),
                          ("boo", "foo", "bar/baz"))
        self.assertEqual(_parse("boo/foo@bar@baz"),
                          (None, "boo", "foo@bar@baz"))
        self.assertEqual(_parse("boo/foo/bar"),
                          (None, "boo", "foo/bar"))
        self.assertEqual(_parse("boo//foo"),
                          (None, "boo", "/foo"))

    def test_noHost(self):
        '''
        Test for failure on no host part.
        '''
        self.assertRaises(InvalidJidError, _parse, "user@")

    def test_doubleAt(self):
        """
        Test for failure on double @ signs.

        This should fail because @ is not a valid character for the host
        part of the JID.
        """
        self.assertRaises(UnicodeError, _parse, "user@@host")

    def test_multipleAt(self):
        """
        Test for failure on two @ signs.

        This should fail because @ is not a valid character for the host
        part of the JID.
        """
        self.assertRaises(UnicodeError, _parse, "user@host@host")

    # Basic tests for case mapping. These are fallback tests for the
    # prepping done in twisted.words.protocols.jabber.xmpp_stringprep

    def test_prepCaseMapUser(self):
        """
        Test case mapping of the user part of the JID.
        """
        self.assertEqual(_prep("UsEr", "host", "resource"),
                          ("user", "host", "resource"))

    def test_prepCaseMapHost(self):
        """
        Test case mapping of the host part of the JID.
        """
        self.assertEqual(_prep("user", "hoST", "resource"),
                          ("user", "host", "resource"))

    def test_prepNoCaseMapResource(self):
        """
        Test no case mapping of the resourcce part of the JID.
        """
        self.assertEqual(_prep("user", "hoST", "resource"),
                          ("user", "host", "resource"))
        self.assertNotEqual(_prep("user", "host", "Resource"),
                            ("user", "host", "resource"))

    def tearDown(self):
        pass


class TestJidObject(unittest.TestCase):

    def setUp(self):
        pass

    def test_ctor_types(self):
        self.assertRaises(ValueError, Jid, b"bytes")

        self.assertRaises(ValueError, Jid, (b"user", "host", "rsrc"))
        self.assertRaises(ValueError, Jid, ("user", b"host", "rsrc"))
        self.assertRaises(ValueError, Jid, ("user", "host", b"rsrc"))

    def tearDown(self):
        pass

    def test_noneArguments(self):
        """
        Test that using no arguments raises an exception.
        """
        self.assertRaises(TypeError, Jid)

    def test_attributes(self):
        """
        Test that the attributes correspond with the JID parts.
        """
        j = Jid("user@host/resource")
        self.assertEqual(j.user, "user")
        self.assertEqual(j.host, "host")
        self.assertEqual(j.resource, "resource")

    def test_userhost(self):
        """
        Test the extraction of the bare JID.
        """
        j = Jid("user@host/resource")
        self.assertEqual("user@host", j.bare)

    def test_userhostOnlyHost(self):
        """
        Test the extraction of the bare JID of the full form host/resource.
        """
        j = Jid("host/resource")
        self.assertEqual("host", j.bare)

    def test_userhostJID(self):
        """
        Test getting a JID object of the bare JID.
        """
        j1 = Jid("user@host/resource")
        j2 = internJid("user@host")
        self.assertEqual(id(j2), id(j1.bare_jid))

    def test_userhostJIDNoResource(self):
        """
        Test getting a JID object of the bare JID when there was no resource.
        """
        j = Jid("user@host")
        self.assertEqual(id(j), id(j.bare_jid))

    def test_fullHost(self):
        """
        Test giving a string representation of the JID with only a host part.
        """
        j = Jid((None, 'host', None))
        self.assertEqual('host', j.full)

    def test_fullHostResource(self):
        """
        Test giving a string representation of the JID with host, resource.
        """
        j = Jid((None, 'host', 'resource'))
        self.assertEqual('host/resource', j.full)

    def test_fullUserHost(self):
        """
        Test giving a string representation of the JID with user, host.
        """
        j = Jid(('user', 'host', None))
        self.assertEqual('user@host', j.full)

    def test_fullAll(self):
        """
        Test giving a string representation of the JID.
        """
        j = Jid(('user', 'host', 'resource'))
        self.assertEqual('user@host/resource', j.full)

    def test_equality(self):
        """
        Test JID equality.
        """
        j1 = Jid("user@host/resource")
        j2 = Jid("user@host/resource")
        self.assertNotEqual(id(j1), id(j2))
        self.assertEqual(j1, j2)

    def test_equalityWithNonJIDs(self):
        """
        Test JID equality.
        """
        j = Jid("user@host/resource")
        try:
            res = (j == "user@host/resource")
        except NotImplementedError:
            pass
        else:
            self.assertFalse("Jid and strings should not be comparable")

    def test_inequality(self):
        """
        Test JID inequality.
        """
        j1 = Jid("user1@host/resource")
        j2 = Jid("user2@host/resource")
        self.assertNotEqual(j1, j2)

    def test_inequalityWithNonJIDs(self):
        """
        Test JID equality.
        """
        j = Jid("user@host/resource")
        self.assertNotEqual(j, 'user@host/resource')

    def test_hashable(self):
        """
        Test JID hashability.
        """
        j1 = Jid("user@host/resource")
        j2 = Jid("user@host/resource")
        self.assertEqual(hash(j1), hash(j2))

    def test_unicode(self):
        """
        Test unicode representation of JIDs.
        """
        j = Jid(('user', 'host', 'resource'))
        self.assertEqual("user@host/resource", j.full)

    def test_repr(self):
        """
        Test representation of JID objects.
        """
        j = Jid(('user', 'host', 'resource'))
        self.assertEqual("Jid('user@host/resource')", repr(j))
