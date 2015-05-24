# -*- coding: utf-8 -*-
import logging
import asyncio
from collections import namedtuple
from base64 import b64decode
from .. import errors

'''XEP-0047'''

log = logging.getLogger(__name__)

RangeTuple = namedtuple("RangeTuple", "offset, length")
FileInfo = namedtuple("FileInfo", "name, size, desc, date, md5, range")

MAX_SEQ = 65535
NS_URI = "http://jabber.org/protocol/ibb"


@asyncio.coroutine
def sendFile(stream, to_jid, filename):
    import ipdb; ipdb.set_trace()


@asyncio.coroutine
def receiveFile(stream, request, file_info):
    open_elem = request.getChild("open", NS_URI)
    if open_elem is None:
        raise error.BadRequestStanzaError("no <open>")

    nsmap = {"ibb": NS_URI}

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

    ft_file = File(file_info)

    # Read data
    while not done:
        data_xp = "/iq[@from='{frm}' and @type='set']"\
                  "/ibb:data[@sid='{sid}']"\
                  .format(frm=from_jid.full, sid=sid)
        close_xp = "/iq[@from='{frm}' and @type='set']"\
                   "/ibb:close[@sid='{sid}']"\
                   .format(frm=from_jid.full, sid=sid)

        iq = yield from stream.wait([(data_xp, nsmap), (close_xp, nsmap)])

        close = iq.getChild("close", NS_URI)
        try:
            if close is not None:
                ft_file.close()
                done = True
            else:
                data = iq.getChild("data", NS_URI)
                ft_file.addBlock(data)
        except Exception as ex:
            import ipdb; ipdb.set_trace()
            # TODO
            pass

        response = iq.resultResponse(clear=True)
        stream.send(response)

    return ft_file


class File:
    def __init__(self, ):
        self.info = info
        self._data_dict = {}
        self._data_size = 0

    def addBlock(self, data):
        seq = int(data.get("seq"))
        if seq in self._data_dict:
            raise ValueError("Duplicate data sequence")

        bytes_ = b64decode(data.text)
        self._data_dict[seq] = bytes_
        num_bytes += len(bytes_)
        self._data_size += num_bytes
        log.info("Adding {} bytes for seq {}".format(num_bytes, seq))
        # TODO: handle MAX_SEQ rollover

    def close(self):

        sequences = sorted([i for i in self._data_dict.keys()])
        if len(sequences) != sequences[-1] + 1:
            # Missing sequences
            seq_set = set(sequences)
            full_set = set([x for x in range(sequences[-1] + 1)])
            if full_set.difference(seq_set):
                # TODO
                raise ValueError("TODO")

        data_size = sum([len(d) for d in self._data_dict.values()])
        if data_size != self.info.size:
            # TODO
            raise ValueError("TODO")

        if self.info.md5:
            # TODO: compare md5
            pass
