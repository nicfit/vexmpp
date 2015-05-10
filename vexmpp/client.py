# -*- coding: utf-8 -*-
import asyncio
import functools
from enum import Enum
from operator import attrgetter
from ipaddress import ip_address

import aiodns

from .jid import Jid
from .stream import Stream, StreamCallbacks
from .errors import Error
from .utils import signalEvent
from .namespaces import CLIENT_NS_URI
from .stanzas import StreamHeader, StreamFeatures, Presence
from .ssl_transport import create_starttls_connection
from .features import sasl, bind, starttls, stream_mgmt
from .protocols import (resourcebind, iqroster, presence, iqversion,
                        entity_time, disco)

DEFAULT_C2S_PORT = 5222

import logging
log = logging.getLogger(__name__)

_dns_cache = {}


class TlsOpts(Enum):
    off = 0
    on = 1
    required = 2

    @staticmethod
    def fromString(s):
        for e in TlsOpts:
            if e.name == s:
                return e
        raise ValueError("Invalid TLS option: {}".format(s))


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
    except aiodns.error.DNSError:
        # No SRV, moving on...
        pass

    # Last resort
    arecord = yield from resolver.query(hostname, 'A')

    ip = arecord.pop()
    _dns_cache[hostname] = ip, port
    return ip, port


class ClientStream(Stream):
    def __init__(self, creds, tls_opt=None, mdm_opt=False, state_callbacks=None,
                 mixins=None, default_timeout=None):
        self._tls_opt = tls_opt or TlsOpts.on
        super().__init__(creds, state_callbacks=state_callbacks, mixins=mixins,
                         default_timeout=default_timeout)

    @asyncio.coroutine
    def _reopenStream(self, timeout=None):
        # Reopen stream
        self._parser_task.reset()
        self.send(StreamHeader(ns=CLIENT_NS_URI, to=self.creds.jid.host))
        # Server <stream:stream>
        header = yield from self.wait(StreamHeader.XPATH, timeout)
        # Server stream:features
        features = yield from self.wait(StreamFeatures.XPATH, timeout)

        return features

    @asyncio.coroutine
    def negotiate(self, timeout=None):
        # <stream:stream>
        stream_stream = StreamHeader(ns=CLIENT_NS_URI, to=self.creds.jid.host)
        self.send(stream_stream)

        # Server <stream:stream>
        _ = yield from self.wait(StreamHeader.XPATH, timeout)

        # Server stream:features
        features = yield from self.wait(StreamFeatures.XPATH, timeout)

        # startttls
        tls_elem = features.getFeature("starttls", starttls.NS_URI)
        if self._tls_opt == TlsOpts.required and tls_elem is None:
            raise Error("TLS required by client but not offered by server.")
        elif (self._tls_opt == TlsOpts.off and tls_elem is not None and
                starttls.isRequired(tls_elem)):
            raise Error("TLS off by client but required by server.")

        if self._tls_opt != TlsOpts.off and tls_elem is not None:
            yield from starttls.handle(self, tls_elem, timeout=timeout)
            features = yield from self._reopenStream(timeout=timeout)

        # SASL auth
        mechs_elem = features.getFeature("mechanisms", sasl.NS_URI)
        if mechs_elem is not None:
            yield from sasl.handle(self, mechs_elem, timeout=timeout)
            features = yield from self._reopenStream(timeout=timeout)
        else:
            raise Error("Missing mechanisms feature")

        # Resource bind
        bind_elem = features.getFeature("bind", resourcebind.NS_URI)
        if bind_elem is None:
            raise Error("Missing bind feature")
        yield from bind.handle(self, bind_elem, timeout=timeout)

        # Stream management
        sm_elem = features.getFeature("sm", stream_mgmt.NS_URI)
        if sm_elem is not None and hasattr(self, "stream_mgmt_opts"):
            yield from stream_mgmt.handle(self, sm_elem,
                                          sm_opts=self.stream_mgmt_opts,
                                          timeout=timeout)
        for mixin in self._mixins:
            yield from mixin.postSession(self)

    @classmethod
    @asyncio.coroutine
    def connect(Class, creds, host=None, port=DEFAULT_C2S_PORT, callbacks=None,
                tls_opt=None, mdm_opt=False, mixins=None,
                timeout=None, loop=None):
        '''Connect and negotiate a stream with the server. The connected stream
        is returned.'''
        loop = loop or asyncio.get_event_loop()
        (host,
         port) = yield from _resolveHostPort(host if host else creds.jid.host,
                                             port, loop)
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

        if mixins is None:
            mixins = Class.createDefaultMixins()
        ProtocolFactory = functools.partial(Class, creds,
                                            state_callbacks=callbacks,
                                            tls_opt=tls_opt,
                                            mdm_opt=mdm_opt,
                                            mixins=mixins,
                                            default_timeout=timeout)

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
            if not connected:
                signalEvent(callbacks, "connectionFailed", peer[0], peer[1], ex)
            else:
                signalEvent(callbacks, "streamError", stream, ex)

            raise

        log.info("%s connected to %s" % (creds.jid.full, peer))
        return stream

    @staticmethod
    def createDefaultMixins():
        return [
                iqroster.RosterMixin(),
                iqversion.IqVersionMixin(),
                entity_time.EntityTimeMixin(),
                presence.PresenceCacheMixin(),
                presence.SubscriptionAckMixin(),
                disco.DiscoCacheMixin(),
               ]

    def sendPresence(self):
        self.send(Presence())


class ClientStreamCallbacks(StreamCallbacks):
    def connecting(self, host, port):
        pass
    def connectionFailed(self, host, port):
        pass
    def sessionStarted(self, stream):
        pass
