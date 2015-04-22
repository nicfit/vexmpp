# -*- coding: utf-8 -*-
import asyncio
import functools
from operator import attrgetter
from ipaddress import ip_address

import aiodns

from .jid import Jid
from .stream import Stream, StreamCallbacks
from .errors import XmppError
from .utils import signalEvent
from .protocols import resourcebind
from .namespaces import CLIENT_NS_URI
from .features import sasl, bind, starttls
from .stanzas import StreamHeader, StreamFeatures
from .ssl_transport import create_starttls_connection

DEFAULT_C2S_PORT = 5222

import logging
log = logging.getLogger(__name__)

_dns_cache = {}


class Credentials(object):
    '''Client credentials, e.g. a user JID and password.'''

    def __init__(self, jid, password):
        if isinstance(jid, str):
            jid = Jid(jid)
        elif not isinstance(jid, Jid):
            raise ValueError("Invalid type: %s" % str(type(jid)))

        self.jid = jid
        self.password = password


@asyncio.coroutine
def _resolveHostPort(hostname, port, loop, use_cache=True):
    global _dns_cache
    if use_cache and hostname in _dns_cache:
        return _dns_cache[hostname]

    resolver = aiodns.DNSResolver(loop=loop)

    ip = None
    try:
        # Given an IP, nothing more to do.
        ip = ip_address(hostname)
        return (str(ip), port)
    except ValueError:
        # Not an IP, move on..,
        pass

    try:
        srv = yield from resolver.query("_xmpp-client._tcp.%s" % hostname,
                                        'SRV')
        srvrecord = sorted(srv, key=attrgetter("priority", "weight"))[0]
        resolved_srv = yield from _resolveHostPort(srvrecord.host,
                                                   srvrecord.port, loop)
        _dns_cache[hostname] = resolved_srv
        return resolved_srv
    except aiodns.error.DNSError as ex:
        # No SRV, moving on...
        pass

    # Last resort
    arecord = yield from resolver.query(hostname, 'A')

    ip = arecord.pop()
    _dns_cache[hostname] = ip, port
    return ip, port


class ClientStream(Stream):
    @asyncio.coroutine
    def negotiate(self, timeout=None):
        # <stream:stream>
        stream_stream = StreamHeader(ns=CLIENT_NS_URI, to=self.creds.jid.host)
        self.send(stream_stream)

        # Server <stream:stream>
        header = yield from self.wait(StreamHeader.XPATH, timeout)

        # Server stream:features
        features = yield from self.wait(StreamFeatures.XPATH, timeout)

        # startttls
        tls_feature = features.getFeature("starttls", starttls.NS_URI)
        tls_active = yield from starttls.handle(self, tls_feature,
                                                timeout=timeout)
        if tls_active:
            # Reopen stream
            self._parser_task.reset()
            self.send(StreamHeader(ns=CLIENT_NS_URI, to=self.creds.jid.host))
            # Server <stream:stream>
            header = yield from self.wait(StreamHeader.XPATH, timeout)
            # Server stream:features
            features = yield from self.wait(StreamFeatures.XPATH, timeout)

        # SASL auth
        mechs_elem = features.getFeature("mechanisms", sasl.NS_URI)
        if mechs_elem is not None:
            yield from sasl.handle(self, mechs_elem, timeout=timeout)
        else:
            raise XmppError("Missing mechanisms feature")

        # Reopen stream
        self._parser_task.reset()
        self.send(StreamHeader(ns=CLIENT_NS_URI, to=self.creds.jid.host))

        # Server <stream:stream>
        header = yield from self.wait(StreamHeader.XPATH, timeout)

        # Server stream:features
        features = yield from self.wait(StreamFeatures.XPATH, timeout)

        # Resource bind
        bind_elem = features.getFeature("bind", resourcebind.NS_URI)
        if bind_elem is None:
            raise XmppError("Missing bind feature")
        yield from bind.handle(self, bind_elem, timeout=timeout)

        for mixin in self._mixins:
            yield from mixin.postSession(self)


class ClientStreamCallbacks(StreamCallbacks):
    def connecting(self, host, port):
        pass
    def connectionFailed(self, host, port):
        pass
    def sessionStarted(self, stream):
        pass


@asyncio.coroutine
def openConnection(creds, host=None, port=DEFAULT_C2S_PORT, callbacks=None,
                   mixins=None, timeout=None, loop=None,
                   StreamClass=ClientStream):
    '''Connect and negotiate a stream with the server. The connected stream
    is returned.'''
    loop = loop or asyncio.get_event_loop()
    (host,
     port) = yield from _resolveHostPort(host if host else creds.jid.host, port,
                                         loop)
    peer = (host, int(port))
    log.verbose("Connecting %s..." % str(peer))

    signalEvent(callbacks, "connecting", peer[0], peer[1])

    # FIXME
    def _sslContext():
        from OpenSSL.SSL import (Context, SSLv23_METHOD, OP_NO_SSLv2,
                                 OP_NO_SSLv3, VERIFY_PEER)
        ssl_ctx = Context(SSLv23_METHOD)
        ssl_ctx.set_options(OP_NO_SSLv2 | OP_NO_SSLv3)
        def _verifyPeerCb(ctx, x509, errno, errdepth, returncode):
            print("errno: %s" % errno)
            print("returncode: %s" % returncode)
            print("errdepth: %s" % errdepth)
            print("x509: %s" % x509)
            print("ctx: %s" % ctx)
            #import ipdb; ipdb.set_trace()
            return True
        #ssl_ctx.set_verify(VERIFY_PEER, _verifyPeerCb)
        return ssl_ctx

    ProtocolFactory = functools.partial(StreamClass, creds,
                                        state_callbacks=callbacks,
                                        mixins=mixins)

    conn = create_starttls_connection(loop, ProtocolFactory, *peer,
                                      use_starttls=True,
                                      ssl_context=_sslContext(),
                                      server_hostname=creds.jid.host)
    try:
        connected = False
        (transport,
         stream) =  yield from asyncio.wait_for(conn, timeout)

        connected = True
        peer = transport.get_extra_info("peername")

        yield from stream.negotiate(timeout=timeout)
        signalEvent(callbacks, "sessionStarted", stream)
    except Exception as ex:
        msg = "Stream negotiation failed" if connected else "Connecting"
        ex_str = str(ex) or ex.__class__.__name__
        log.error("%s failed (%s): %s" % (msg, creds.jid.full, ex_str))

        if not connected:
            signalEvent(callbacks, "connectionFailed", peer[0], peer[1], ex)
        else:
            signalEvent(callbacks, "streamError", stream, ex)

        raise

    log.info("%s connected to %s" % (creds.jid.full, peer))
    return stream
