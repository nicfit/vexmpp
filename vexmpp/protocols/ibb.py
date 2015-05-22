# -*- coding: utf-8 -*-
import asyncio
from collections import namedtuple
from .. import errors

'''XEP-0047'''

RangeTuple = namedtuple("RangeTuple", "offset, length")
FileInfo = namedtuple("FileInfo", "name, size, desc, date, md5, range")

MAX_SEQ = 65535
NS_URI = "http://jabber.org/protocol/ibb"


@asyncio.coroutine
def receiveFile(stream, request, file_info, timeout=None):
    open_elem = request.getChild("open", NS_URI)
    if open_elem is None:
        raise error.BadRequestStanzaError("no <open>")

    from_jid = request.frm
    block_size = open_elem.get("block-size")
    sid = open_elem.get("sid")
    stanza = open_elem.get("iq")
    if block_size is None or sid is None:
        raise error.BadRequestStanzaError("Missing block-size and/or sid")
    elif stanza == "message":
        raise FeatureNotImplementedStanzaError("IBB via messages not supported")

    seq = 0
    done = False
    file_data = b""
    response = request.resultResponse()
    stream.send(response)

    # Read data
    while not done:
        xp = "/iq[@from='{frm}' and @type='set']"\
             "/ibb:data[@seq='{seq:d}' and @sid='{sid}']"\
             .format(frm=from_jid.full, seq=seq, sid=sid)
        data = yield from stream.wait((xp, {"ibb": NS_URI}), timeout=timeout)
        print("GOT SEQ {}".format(seq))
        seq += 1
        if seq > MAX_SEQ:
            seq = 0

