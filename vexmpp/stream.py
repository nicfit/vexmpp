# -*- coding: utf-8 -*-
import os
import asyncio

import logging
log = logging.getLogger(__name__)

from lxml import etree

from . import stanzas
from .stanzas import Iq
from .parser import Parser
from .utils import signalEvent


if "VEX_TIMED_WAITS" in os.environ and int(os.environ["VEX_TIMED_WAITS"]):
    from .utils import benchmark as timedWait
    from .metrics import ValueMetric
    stream_wait_met = ValueMetric("stream:wait_time", type_=float)
else:
    stream_wait_met = None
    class timedWait:
        '''no-op context manager'''
        def __enter__(self):
            return None
        def __exit__(self, ty, val, tb):
            return False

_ENFORCE_TIMEOUTS = bool("VEX_ENFORCE_TIMEOUTS" in os.environ and
                         int(os.environ["VEX_ENFORCE_TIMEOUTS"]))


class ParserTask(asyncio.Task):
    def __init__(self, stream, loop=None):
        super().__init__(self._run(), loop=loop)
        self._parser = Parser()
        self._data_queue = asyncio.Queue()
        self._stream = stream

    def parse(self, bytes_):
        self._data_queue.put_nowait(bytes_)

    def reset(self):
        self._parser.reset()

    @asyncio.coroutine
    def _run(self):
        try:
            while True:
                data = yield from self._data_queue.get()
                elems = self._parser.parse(data)
                for e in elems:
                    stanza = stanzas.makeStanza(e)
                    log.verbose('[STANZA IN]: %s' %
                                stanza.toXml(pprint=True).decode("utf-8"))
                    yield from self._stream._handleStanza(stanza)
        except Exception as ex:
            log.exception(ex)
            raise


class Stream(asyncio.Protocol):
    '''Base class for XMPP streams.'''

    def __init__(self, creds, state_callbacks=None, mixins=None,
                 default_timeout=None):
        self.creds = creds
        self._transport = None
        self._waiter_queues = []
        self._tls_active = False
        self._callbacks = state_callbacks

        self._mixins = mixins or []
        for mixin in self._mixins:
            for name, obj in mixin._exports:
                if name in self.__dict__:
                    raise ValueError("Mixin '%s' exports ambiguous "
                                     "data named '%s'" % (str(mixin), name))
                else:
                    # Add the symbol to the stream's namespace
                    self.__dict__[name] = obj

        self._parser_task = ParserTask(self)
        self.default_timeout = default_timeout
        # Stream errors
        self.error = None

    @property
    def connected(self):
        if not self._transport:
            return False
        else:
            if (getattr(self._transport, "_closing") and
                    self._transport._closing):
                # SSL transport
                return False

        return True

    @property
    def tls_active(self):
        return self._tls_active

    @property
    def jid(self):
        return self.creds.jid

    def close(self):
        if self.connected:
            self.send(b"</stream:stream>")
            self._transport.close()

    def send(self, data):
        '''Send ``data`` which can be a vexmpp.stanza.Stanza,
         lxml.etree.Element, a str, or bytes. The the case of bytes the
         encoding MUST be utf-8 encoded (per XMPP specification).

         In the case of Stanza and Element the Mixin.onSend callback is
         invoked. Currently there is not a Mixin callback for strings or bytes.
        '''
        def _send(bytes_):
            if not self._transport:
                log.warn("Data send with disconnected transport")
                return

            self._transport.write(bytes_)
            log.debug("[BYTES OUT]: %s", bytes_)

        stanza = None
        if isinstance(data, stanzas.Stanza):
            stanza = data
            _send(data.toXml())
        elif isinstance(data, str):
            _send(data.encode("utf-8"))
        elif isinstance(data, etree._Element):
            stanza = stanzas.Stanza(xml=data)
            _send(etree.tostring(data, encoding="utf-8"))
        elif isinstance(data, bytes):
            _send(data)
        else:
            raise ValueError("Unable to send type {}".format(type(data)))

        if stanza:
            for m in self._mixins:
                m.onSend(self, stanza)

    @asyncio.coroutine
    def sendAndWaitIq(self, child_ns, to=None, child_name="query", type="get",
                      raise_on_error=False, timeout=None, id_prefix=None):
        iq = Iq(to=to, type=type, request=(child_name, child_ns),
                id_prefix=id_prefix)
        resp = yield from self.sendAndWait(iq, raise_on_error=raise_on_error,
                                           timeout=timeout)
        return resp

    @asyncio.coroutine
    def sendAndWait(self, stanza, raise_on_error=False, timeout=None):
        if not stanza.id:
            stanza.setId()

        xpath = "/%s[@id='%s']" % (stanza.name, stanza.id)
        self.send(stanza)
        resp = yield from self.wait([(xpath, None)], timeout=timeout)

        if resp.error is not None and raise_on_error:
            raise resp.error
        else:
            return resp

    @asyncio.coroutine
    def negotiate(self, timeout=None):
        raise NotImplementedError()

    @asyncio.coroutine
    def wait(self, xpaths, timeout=None):
        '''``xpaths`` is a 2-tuple of the form (xpath, nsmap), or a list of
        the same tuples to wait on a choice of matches. The first matched
        stanza is returned. Passing a ``timeout`` argument will raise a
        asyncio.TimeoutError if not matches are found.'''
        global stream_wait_met

        if not isinstance(xpaths, list):
            xpaths = [xpaths]

        log.debug("Stream wait for %s [timeout=%s]" % (xpaths, timeout))
        if _ENFORCE_TIMEOUTS and not timeout:
            raise RuntimeError("Timeout not set error")

        queue = asyncio.JoinableQueue()
        self._waiter_queues.append(queue)

        while True:
            try:
                with timedWait() as timer_stat:
                    stanza = yield from asyncio.wait_for(queue.get(), timeout)
                if stream_wait_met:
                    stream_wait_met.update(timer_stat["total"])
                    log.debug("Stream wait - time: {:.3f} "
                              "min/max/avg: {:.6f}/{:.6f}/{:.6f}"
                           .format(stream_wait_met.value,
                                   stream_wait_met.min, stream_wait_met.max,
                                   stream_wait_met.average))
            except asyncio.TimeoutError as ex:
                raise asyncio.TimeoutError(
                  "Timeout ({}s) while waiting for xpaths: {}".format(timeout,
                                                                      xpaths))
            for xp, nsmap in xpaths:
                if stanza.xml.xpath(xp, namespaces=nsmap):
                    self._waiter_queues.remove(queue)
                    queue.task_done()
                    return stanza
            queue.task_done()

    # asyncio.Protocol implementation
    def connection_made(self, transport, tls=False):
        log.debug("Connection_made: %s", transport)
        self._transport = transport
        self._tls_active = tls
        signalEvent(self._callbacks, "connected", self, tls)

    def starttls_made(self, transport):
        self.connection_made(transport, tls=True)

    @asyncio.coroutine
    def _handleStanza(self, stanza):
        if isinstance(stanza, stanzas.StreamError):
            signalEvent(self._callbacks, "streamError", self, stanza)
            self._transport.close()
            return

        for m in self._mixins:
            yield from m.onStanza(self, stanza)

        if self._waiter_queues:
            for q in self._waiter_queues:
                q.put_nowait(stanza)
                yield from q.join()

    # asyncio.Protocol implementation
    def data_received(self, data):
        log.debug('[BYTES IN]: {!r}'.format(data.decode()))
        self._parser_task.parse(data)

    # asyncio.Protocol implementation
    def connection_lost(self, reason):
        self._transport = None
        self._tls_active = False
        log.debug('The server closed the connection: %s' % str(reason))
        signalEvent(self._callbacks, "disconnected", self, reason)

    @property
    def default_timeout(self):
        return self._default_timeout

    @default_timeout.setter
    def default_timeout(self, t):
        if t is not None:
            t = int(t)
        self._default_timeout = t


class Mixin(object):
    def __init__(self, export_tuples=None):
        '''
        ``export_tuples`` is a list of 2-tuples (name, obj) that added to the
        stream object's __dict__, as in __dict__[name] = obj.  By default no
        values are exported.
        '''
        self._exports = export_tuples if export_tuples else []

    @asyncio.coroutine
    def postSession(self, stream):
        '''Called after stream negotiation and session creation.'''
        pass

    @asyncio.coroutine
    def onStanza(self, stream, stanza):
        '''Called for each incoming Stanza.

        See :func:`vexmpp.utils.xpathFilter` for a decorator that can filter
        only the stanzas the implementation is interested in.
        '''
        pass

    def onSend(self, stream, stanza):
        '''Called for each outgoing stanza.'''
        pass


class StreamCallbacks:
    def connected(self, stream, tls_active):
        pass
    def disconnected(self, stream, reason):
        pass
    def streamError(self, stream, error):
        pass

