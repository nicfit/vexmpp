# -*- coding: utf-8 -*-
import asyncio
from ..stanzas import Stanza
from ..errors import makeStanzaError
from ..protocols.stream_mgmt import NS_URI


@asyncio.coroutine
def handle(stream, feature_elem, sm_opts, timeout=None):
    assert(feature_elem is not None)
    nsmap = {"sm": NS_URI}

    enable_elem = Stanza("enable", nsmap={None: NS_URI})
    if sm_opts and sm_opts.resume:
        enable_elem._setAttr("resume", "true")
    stream.send(enable_elem)

    resp = yield from stream.wait([("/sm:enabled", nsmap),
                                   ("/sm:failed", nsmap)], timeout=timeout)
    if resp.name == "{%s}failed" % NS_URI:
        raise makeStanzaError(resp.xml)

    sm_opts.sm_id = resp._getAttr("id")
    sm_opts.resume = bool(resp._getAttr("resume") and
                          resp._getAttr("resume") in ("1", "true"))
    sm_opts.resume_location = resp._getAttr("location")
    sm_opts.max_resume_time = resp._getAttr("max")

    return True
