# -*- coding: utf-8 -*-
from xml.parsers import expat
from lxml import etree
from collections import deque

from .namespaces import STREAM_NS_URI, CLIENT_NS_URI, SERVER_NS_URI


class ParseError(RuntimeError):
    def __init__(self, msg, state):
        super(ParseError, self).__init__(msg)
        self.parser_state = state


class Parser(object):
    def __init__(self):
        self._expat = None
        self._curr = None

        self._stanzas = deque()

        class ParseState(object):
            def __init__(self):
                self.last_data = b""
                self.end_of_stream = False
                self.reset()

            def reset(self):
                self.nsmap = {}
                self.level = 0
                self.elem = None
        self._curr = ParseState()

        self.reset()

    def reset(self):
        log.debug("Resetting expat parser")

        self._expat = expat.ParserCreate("utf-8", " ")
        self._expat.StartNamespaceDeclHandler = self._onStartNamespace
        self._expat.StartElementHandler = self._onStartElement
        self._expat.EndElementHandler = self._onEndElement
        self._expat.CharacterDataHandler = self._onCharData

        self._curr.reset()

    def _onStartNamespace(self, prefix, uri):
        self._curr.nsmap[prefix] = uri

    @staticmethod
    def isStreamHeader(e):
        return e.tag == "{%s}stream" % STREAM_NS_URI

    @staticmethod
    def isStreamError(e):
        return e.tag == "{%s}error" % STREAM_NS_URI

    def parse(self, data):
        if self._curr.end_of_stream:
            # Peer sent </stream:stream>
            self._curr.reset()

        self._curr.last_data += data
        try:
            self._expat.Parse(data)
        except expat.ExpatError as ex:
            raise ParseError(str(ex), self._curr)
        else:
            self._curr.last_data = b""  # No ExpatError, clear state buffer

        parsed_stanzas = []
        if self._stanzas:
            parsed_stanzas += [s for s in self._stanzas]
            self._stanzas.clear()
        return parsed_stanzas

    def _onStartStreamElement(self, name):
        assert(self._curr.elem is None)

        nsmap = {"stream": STREAM_NS_URI}
        if name == "stream":
            nsmap[None] = self._curr.nsmap[None]
        tag = "{%s}%s" % (STREAM_NS_URI, name)

        elem = etree.Element(tag, nsmap=nsmap)

        return elem

    def _onStartStanzaElement(self, name, ns):
        assert(self._curr.elem is None)

        nsmap = None if ns in [CLIENT_NS_URI, SERVER_NS_URI] else {None: ns}
        tag = "{%s}%s" % (ns, name) if nsmap else name

        elem = etree.Element(tag, nsmap=nsmap)

        return elem

    def _onStartChildElement(self, name, ns):
        assert(self._curr.elem is not None)

        nsmap = None if ns in [CLIENT_NS_URI, SERVER_NS_URI] else {None: ns}
        tag = "{%s}%s" % (ns, name) if nsmap else name

        elem = etree.Element(tag, nsmap=nsmap)
        return elem

    def _onStartElement(self, name, attrs):
        # name is 'ns<space>name'
        elem_ns, elem_name = name.split()

        if elem_ns == STREAM_NS_URI:
            elem = self._onStartStreamElement(elem_name)
        elif self._curr.elem is None:
            elem = self._onStartStanzaElement(elem_name, elem_ns)
        else:
            elem = self._onStartChildElement(elem_name, elem_ns)

        for a in attrs:
            if " " in a:
                # XXX: should these even be supported?
                # Namespaced attribute, a is "ns<space>name"
                a_ns, a = a.split()
                elem.attrib["{%s}%s" % (a_ns, a)] = attrs["%s %s" % (a_ns, a)]
            else:
                elem.attrib[a] = attrs[a]

        if self.isStreamHeader(elem):
            self._curr.elem = None
            self._stanzas.append(elem)
        else:
            self._curr.level += 1
            if self._curr.elem is not None:
                self._curr.elem.append(elem)
            self._curr.elem = elem

    def _onEndElement(self, name):
        if tuple(name.split()) == (STREAM_NS_URI, "stream"):
            self._curr.end_of_stream = True
            return

        self._curr.level -= 1
        if self._curr.level == 0:
            self._stanzas.append(self._curr.elem)
            self._curr.reset()
        else:
            if self._curr.elem is not None:
                self._curr.elem = self._curr.elem.getparent()

    def _onCharData(self, data):
        if self._curr.elem is not None and len(data.strip()):
            if self._curr.elem.text is None:
                self._curr.elem.text = data
            else:
                self._curr.elem.text += data


from . import getLogger
log = getLogger(__name__)
