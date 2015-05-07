#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import asyncio
from getpass import getpass

import aiodns
import OpenSSL.SSL

try:
    from pygments import highlight
    from pygments.lexers import XmlLexer
    from pygments.formatters import TerminalFormatter
    _has_pygments = True
except:
    _has_pygments = False

from vexmpp.jid import Jid
from vexmpp.errors import XmppError
from vexmpp.application import Application
from vexmpp.core import openConnection
from vexmpp.client import (Credentials, DEFAULT_C2S_PORT,
                           ClientStreamCallbacks)
from vexmpp.stanzas import Presence
from vexmpp.protocols import iqversion
from vexmpp.utils import ArgumentParser


def _outputXml(stanza):
    xml = stanza.toXml(pprint=True, encoding="utf-8")
    if _has_pygments:
        xml = highlight(xml, XmlLexer(), TerminalFormatter())
    print(xml)


@asyncio.coroutine
def main(app):
    args = app.args

    if "VEX_PASSWD" in os.environ:
        password = os.environ["VEX_PASSWD"]
    else:
        password = getpass("Password for '%s': " % args.jid)
    jid = Jid(args.jid)
    if not jid.resource:
        jid = Jid((jid.user, jid.host, "vex"))

    try:
        stream = yield from openConnection(Credentials(jid, password),
                                           host=jid.host, port=args.port,
                                           callbacks=Callbacks(),
                                           timeout=5)
    except asyncio.TimeoutError:
        print("Connection timed out", file=sys.stderr)
        return 1
    except XmppError as ex:
        print("Authentication error: %s" % str(ex), file=sys.stderr)
        return 2
    except OpenSSL.SSL.Error as ex:
        print("SSL error: %s" % str(ex), file=sys.stderr)
        return 3
    except aiodns.error.DNSError as ex:
        print("DNS resolution failure.", file=sys.stderr)
        return 5

    # Server version
    server_version = yield from iqversion.get(stream, jid.host, timeout=10)
    _outputXml(server_version)

    # Initial presence
    stream.send(Presence())

    if args.disconnect:
        stream.close()
        return 0

    while True:
        try:
            stanza = yield from stream.wait(("/*", None), timeout=10)
            _outputXml(stanza)
        except asyncio.TimeoutError:
            pass

    return 0


class Callbacks(ClientStreamCallbacks):

    def disconnected(self, stream, reason):
        print(("disconnected", stream, reason))
        self._shutdown()

    def connectionFailed(self, host, port, reason):
        print(("connectionFailed", host, port, reason))
        self._shutdown()

    def _shutdown(self):
        global app
        app.event_loop.stop()

    def connecting(self, host, port):
        print(("connecting", host, port))

    def sessionStarted(self, stream):
        print(("sessionStarted", stream))

    def connected(self, stream, tls_active):
        print(("connected", stream, tls_active))

    def streamError(self, stream, error):
        print(("streamError", stream, error))


arg_parser = ArgumentParser(
    description="Simple XMPP client. The user will be prompted for a login "
                "password unless the environment variable VEX_PASSWD is set.")
arg_parser.add_argument("jid", help="Jabber ID for login")
arg_parser.add_argument("--host", help="Alternative server for connecting")
arg_parser.add_argument("--port", type=int, default=DEFAULT_C2S_PORT,
                        help="Alternative port for connecting")
arg_parser.add_argument("--disconnect", action="store_true",
                        help="Disconnect once stream negotiation completes."
                       )
app = Application(main, argument_parser=arg_parser)
sys.exit(app.run())
