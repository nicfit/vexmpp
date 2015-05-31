# -*- coding: utf-8 -*-
import asyncio
import platform
from lxml import etree

from .. import __projectname__, __version__
from ..stanzas import Iq
from ..stream import Mixin
from ..utils import xpathFilter

import logging
log = logging.getLogger(__name__)


NS_URI = "jabber:iq:version"
GET_XPATH = ("/iq[@type='get']/ns:query", {"ns": NS_URI})


@asyncio.coroutine
def get(stream, to, timeout=None):
    iq = yield from stream.sendAndWaitIq(NS_URI, to=to, raise_on_error=True,
                                         id_prefix="version_get",
                                         timeout=timeout)
    return iq


class IqVersionMixin(Mixin):
    '''A stream mixin for handling version IQ 'get' requests.'''

    def __init__(self, name=__projectname__, version=__version__,
                 show_platform=True):
        super().__init__()

        self._name = str(name)
        self._version = str(version)
        self._show_platform = show_platform

    @xpathFilter(GET_XPATH)
    @asyncio.coroutine
    def onStanza(self, stream, stanza):
        log.debug("jabber:iq:version received")

        result = Iq(xml=stanza.xml)
        result.swapToFrom()
        result.type = "result"

        elem = etree.Element("name")
        elem.text = self._name
        result.query.append(elem)

        elem = etree.Element("version")
        elem.text = self._version
        result.query.append(elem)

        if self._show_platform:
            elem = etree.Element("os")
            elem.text = "%s, %s, %s" % (platform.system(), platform.release(),
                                        platform.version())
            result.query.append(elem)

        stream.send(result)
