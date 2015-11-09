# -*- coding: utf-8 -*-
import asyncio
from ..stream import Mixin
from ..utils import xpathFilter

from ..log import getLogger
log = getLogger(__name__)

NS_URI = "urn:xmpp:sm:3"


class Opts():
    resume = False
    sm_id = None
    resume_location = None
    max_resume_time = None


class Mixin(Mixin):
    '''XXX: this is a very rudimentary XEP-0198 Mixin. Currently all it does
    is count stanza in and out.'''

    def __init__(self, opts=None):
        self._opts = opts or Opts()
        self._in_count = 0
        self._out_count = 0
        super().__init__([('stream_mgmt_opts', self._opts)])

    @xpathFilter(["/iq", "/presence", "/message",
                  ("/ns:a", {"ns": NS_URI}), ("/ns:r", {"ns": NS_URI}),
                 ])
    @asyncio.coroutine
    def onStanza(self, stream, stanza):
        self._in_count += 1
        log.debug("Stanza IN count: {:d}".format(self._in_count))

    @xpathFilter(["/iq", "/presence", "/message"])
    def onSend(self, stream, stanza):
        self._out_count += 1
        log.debug("Stanza OUT count: {:d}".format(self._out_count))
