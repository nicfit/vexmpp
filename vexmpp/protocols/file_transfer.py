# -*- coding: utf-8 -*-
import os
import asyncio
from hashlib import md5
from pathlib import Path
from tempfile import mkstemp
from base64 import b64decode, b64encode
from collections import namedtuple

from lxml import etree

from ..log import getLogger
log = getLogger(__name__)

from ..errors import *
from ..protocols import xdata
from ..stanzas import Iq

SI_NS_URI = "http://jabber.org/protocol/si"
FT_NS_URI = "http://jabber.org/protocol/si/profile/file-transfer"
FEATURE_NS_URI = "http://jabber.org/protocol/feature-neg"

IBB_NS_URI = "http://jabber.org/protocol/ibb"
BYTESTREAMS_NS_URI = "http://jabber.org/protocol/bytestreams"

RangeTuple = namedtuple("RangeTuple", "offset, length")
# FIXME: Collapse into File class. Lazy open temp file
FileInfo = namedtuple("FileInfo", "name, size, desc, date, md5, range, sid")

MAX_SEQ = 65535
BLOCK_SIZE = 4096


class FileTransferError(Exception):
    pass


class File:
    def __init__(self, info, maxsize=None, tempdir=None):
        self.info = info
        self._data_size = 0
        self._next_seq = None
        self._seq_set = set()
        self._md5sum = md5()
        self._maxsize = maxsize

        self._tmp_dir = Path(tempdir).resolve()
        (self._tmp_fd,
         self._tmp_name) = mkstemp(suffix=".incoming", dir=str(self._tmp_dir))
        log.debug("Opened tmp file {}".format(self._tmp_name))

    def addBlock(self, data):
        if not self._tmp_fd:
            raise ValueError("File object has not been opened.")

        if self._next_seq is None:
            self._next_seq = 0

        try:
            seq = int(data.get("seq"))
            if seq in self._seq_set:
                raise ValueError("Duplicate data sequence.")
            elif seq != self._next_seq:
                raise ValueError("Data sequence out of order.")

            self._seq_set.add(seq)
            self._next_seq += 1

            bytes_ = b64decode(data.text)
            num_bytes = len(bytes_)
            self._data_size += num_bytes
            if self._maxsize and self._data_size > self._maxsize:
                raise OverflowError("File exceeds size limit of {:d} bytes."
                                    .format(self._maxsize))
        except:
            self.close(False)
            raise

        os.write(self._tmp_fd, bytes_)
        self._md5sum.update(bytes_)
        log.info("Writing {} bytes for seq {}".format(num_bytes, seq))

        # TODO: handle MAX_SEQ rollover

    def _cleanupTemp(self):
        if os.path.isfile(self._tmp_name):
            os.remove(self._tmp_name)
        self._tmp_name = None

    def _verify(self):
        sequences = sorted(self._seq_set)
        if len(sequences) != sequences[-1] + 1:
            # Missing sequences
            full_set = set(range(sequences[-1] + 1))
            if full_set.difference(self._seq_set):
                raise FileTransferError("Not all data blocks received, missing "
                                        "sequences {}".format(
                                        full_set.difference(self._seq_set)))

        if self._data_size != self.info.size:
            raise FileTransferError("Not all bytes received, read {:d} bytes "
                                    "but expected {:d}".format(self._data_size,
                                                               self.info.size))

        if self.info.md5:
            md5 = self.md5
            if self.info.md5.lower() != md5:
                raise FileTransferError("File hash mismatch, computed {} but "
                                        "expected {}".format(md5,
                                                             self.info.md5))

    def close(self, success):
        close_err = None

        if self._tmp_fd:
            os.close(self._tmp_fd)
            log.debug("Closed tmp file {}".format(self._tmp_name))
            self._tmp_fd = None

        if success:
            try:
                self._verify()
            except Exception as ex:
                close_err = ex

        if not success or close_err:
            self._cleanupTemp()

        if close_err:
            raise close_err

    @property
    def md5(self):
        return self._md5sum.hexdigest()

    @property
    def filename(self):
        return self._tmp_name


@asyncio.coroutine
def receiveFile(stream, si_request, maxsize=None, tempdir=None, timeout=None):
    no_valid_streams_error = etree.Element("no-valid-streams",
                                           nsmap={None: SI_NS_URI})

    si_elem = si_request.find("./si:si", namespaces={"si": SI_NS_URI})
    try:
        if si_elem.attrib["profile"] != FT_NS_URI:
            raise BadRequestStanzaError("Profile not understood",
                    app_err=etree.Element("bad-profile",
                                          nsmap={None: SI_NS_URI}))
        sid = si_elem.attrib["id"]

        file_elem = si_request.find(".//f:file", namespaces={"f": FT_NS_URI})
        form = si_request.find(".//f:feature/x:x[@type='form']",
                            namespaces={"x": "jabber:x:data",
                                        "f": FEATURE_NS_URI})
        if file_elem is None:
            raise BadRequestStanzaError("no <file> child")
        elif form is None:
            raise BadRequestStanzaError("no x-data form")

        form = xdata.XdataForm(form)
        field = form.field("stream-method")
        if field is None:
            raise BadRequestStanzaError("no stream-method field",
                                        app_err=no_valid_streams_error)

        # XXX: Field class with nice accessors,  etc.. 
        methods = field.xpath("./x:option/x:value/text()",
                              namespaces={"x": xdata.NS_URI})

        if (IBB_NS_URI not in methods):
            raise BadRequestStanzaError("Only in-band-bytestreams is supported",
                                    app_err=no_valid_streams_error)
    except XmppError as err:
        stream.send(si_request.errorResponse(err))
        raise FileTransferError(str(err))

    # TODO: check and prefer bytesstream here.
    selected_meth = IBB_NS_URI
    receiveFileCoro = ibbReceiveFile
    open_xpath = ("/iq[@type='set']/ibb:open[@sid='{}']".format(sid),
                  {"ibb": IBB_NS_URI})

    range_elem = file_elem.find("./{%s}range" % FT_NS_URI)
    range_info = None
    if range_elem is not None:
        r_offset = range_elem.get("offset")
        r_length = range_elem.get("length")
        if (r_offset, r_length) != (None, None):
            range_info = RangeTuple(offset=int(r_offset), length=int(r_length))

    file_info = FileInfo(name=file_elem.get("name"),
                         size=int(file_elem.get("size")),
                         desc=file_elem._getChildText("desc"),
                         date=file_elem.get("date"),
                         md5=file_elem.get("hash"),
                         range=range_info,
                         sid=sid)

    form.type = "submit"
    field.clear()
    field.set("var", "stream-method")
    e = etree.Element("value")
    e.text = selected_meth
    field.append(e)

    response = si_request.resultResponse()
    stream.send(response)

    open_iq = yield from stream.wait(open_xpath, timeout=timeout)
    new_file = yield from receiveFileCoro(stream, open_iq, file_info,
                                          maxsize=maxsize, tempdir=tempdir,
                                          timeout=timeout)
    return new_file


@asyncio.coroutine
def sendFile(stream, to_jid, filename, description=None, timeout=None):
    request = Iq(to=to_jid, type="set", request=("si", SI_NS_URI))
    sid = request.id

    h = md5()
    path = Path(filename)
    h.update(path.open("rb").read())

    # FIXME: date .. need a xmpp date format util
    file_info = FileInfo(name=path.name, size=path.stat().st_size,
                         desc=description, date=None, md5=h.hexdigest(),
                         range=None, sid=sid)

    si = request.query
    si.attrib["id"] = sid
    si.attrib["profile"] = FT_NS_URI

    f = si.appendChild("file", FT_NS_URI)
    f.attrib["name"] = file_info.name
    f.attrib["size"] = str(file_info.size)
    if description:
        f.appendChild("desc").text = description
    if file_info.md5:
        f.attrib["hash"] = file_info.md5
    if file_info.date:
        f.attrib["date"] = date
    # TODO: ranges

    feat = si.appendChild("feature", FEATURE_NS_URI)
    form = xdata.XdataForm()
    form.appendListField("stream-method", [IBB_NS_URI], default=IBB_NS_URI)
    feat.append(form)

    # Initiate stream
    try:
        response = yield from stream.sendAndWait(request, timeout=timeout,
                                                 raise_on_error=True)
    except XmppError as ex:
        raise FileTransferError(ex)

    si_elem = response.find("./si:si", namespaces={"si": SI_NS_URI})
    methods = si_elem.xpath(".//x:field/x:value/text()",
                            namespaces={"x": xdata.NS_URI})
    if not methods or (methods[0] not in [IBB_NS_URI]):
        stream.send(response.errrorResponse(BadRequestStanzaError(
                "Only in-band-bytestreams is supported",
                app_err=etree.Element("no-valid-streams",
                                      nsmap={None: SI_NS_URI}))))
        raise FileTransferError("No supported stream methods.")

    # TODO: check and prefer bytesstream here.
    selected_meth = IBB_NS_URI
    sendFileCoro = ibbSendFile

    open_iq = Iq(to=to_jid, type="set", request=("open", selected_meth))
    open_iq.query.attrib["sid"] = sid
    open_iq.query.attrib["block-size"] = str(BLOCK_SIZE)
    open_iq.query.attrib["stanza"] = "iq"

    try:
        _ = yield from stream.sendAndWait(open_iq, raise_on_error=True,
                                          timeout=timeout)
        yield from sendFileCoro(stream, to_jid, path, sid, timeout=timeout)

    except XmppError as ex:
        raise FileTransferError(ex)


### IBB ###

@asyncio.coroutine
def ibbSendFile(stream, to_jid, file_path, sid, block_size=BLOCK_SIZE,
                timeout=None):
    assert(isinstance(file_path, Path))

    open_iq = Iq(to=to_jid, type="set", request=("open", IBB_NS_URI))
    open_iq.query.attrib["sid"] = sid
    open_iq.query.attrib["block-size"] = str(block_size)
    open_iq.query.attrib["stanza"] = "iq"

    _ = yield from stream.sendAndWait(open_iq, raise_on_error=True,
                                      timeout=timeout)

    with file_path.open("rb") as fp:
        seq = 0
        while True:
            data = fp.read(BLOCK_SIZE)
            if not data:
                break
            iq = Iq(to=to_jid, type="set", request=("data", IBB_NS_URI))
            iq.query.attrib["sid"] = sid
            iq.query.attrib["seq"] = str(seq)
            iq.query.text = b64encode(data)
            _ = yield from stream.sendAndWait(iq, raise_on_error=True,
                                              timeout=timeout)
            seq += 1

    close_iq = Iq(to=to_jid, type="set", request=("close", IBB_NS_URI))
    close_iq.query.attrib["sid"] = sid
    _ = yield from stream.sendAndWait(close_iq, raise_on_error=True,
                                      timeout=timeout)


@asyncio.coroutine
def ibbReceiveFile(stream, request, file_info, maxsize=None, tempdir=None,
                   timeout=None):


    open_elem = request.getChild("open", IBB_NS_URI)
    if open_elem is None:
        raise BadRequestStanzaError("no <open>")

    nsmap = {"ibb": IBB_NS_URI}

    from_jid = request.frm
    block_size = open_elem.get("block-size")
    sid = open_elem.get("sid")
    stanza = open_elem.get("iq")
    if block_size is None or sid is None:
        raise BadRequestStanzaError("Missing block-size and/or sid")
    elif stanza == "message":
        raise FeatureNotImplementedStanzaError("IBB via messages not supported")

    seq = 0
    done = False
    file_data = b""
    response = request.resultResponse()
    stream.send(response)

    ft_file = File(file_info, maxsize, tempdir=tempdir)

    # Read data
    while not done:
        data_xp = "/iq[@from='{frm}' and @type='set']"\
                  "/ibb:data[@sid='{sid}']"\
                  .format(frm=from_jid.full, sid=sid)
        close_xp = "/iq[@from='{frm}' and @type='set']"\
                   "/ibb:close[@sid='{sid}']"\
                   .format(frm=from_jid.full, sid=sid)

        try:
            iq = yield from stream.wait([(data_xp, nsmap), (close_xp, nsmap)],
                                        timeout=timeout)
        except asyncio.TimeoutError:
            ft_file.close(False)
            raise

        close = iq.getChild("close", IBB_NS_URI)
        if close is not None:
            ft_file.close(True)
            done = True
        else:
            data = iq.getChild("data", IBB_NS_URI)
            try:
                ft_file.addBlock(data)
            except (ValueError, OverflowError) as ex:
                m = str(ex)
                if isinstance(ex, OverflowError):
                    xmpp_error = PolicyViolationStanzaError(m)
                else:
                    xmpp_error = BadRequestStanzaError(m)
                stream.send(iq.errorResponse(xmpp_error))
                raise FileTransferError(m)

        response = iq.resultResponse(clear=True)
        stream.send(response)

    return ft_file
