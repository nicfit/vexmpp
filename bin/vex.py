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
from vexmpp.client import (Credentials, openConnection, DEFAULT_C2S_PORT,
                           ClientStreamCallbacks)
from vexmpp.stanzas import Presence
from vexmpp.protocols import iqroster, presence, iqversion, entity_time
from vexmpp.utils import ArgumentParser


def _outputXml(stanza):
    xml = stanza.toXml(pprint=True, encoding="utf-8")
    if _has_pygments:
        xml = highlight(xml, XmlLexer(), TerminalFormatter())
    print(xml)


@asyncio.coroutine
def main(app):
    description = "Simple XMPP client. The user will be prompted for a login "\
                  "password unless the environment variable VEX_PASSWD is set."
    arg_parser = ArgumentParser(description=description)
    arg_parser.add_argument("jid", help="Jabber ID for login")
    arg_parser.add_argument("--host", help="Alternative server for connecting")
    arg_parser.add_argument("--port", type=int, default=DEFAULT_C2S_PORT,
                            help="Alternative port for connecting")
    arg_parser.add_argument("--disconnect", action="store_true",
                            help="Disconnect once stream negotiation completes."
                           )

    args = arg_parser.parse_args()

    if "VEX_PASSWD" in os.environ:
        password = os.environ["VEX_PASSWD"]
    else:
        password = getpass("Password for '%s': " % args.jid)
    jid = Jid(args.jid)
    if not jid.resource:
        jid = Jid((jid.user, jid.host, "vex"))

    mixins = [iqroster.RosterMixin(),
              iqversion.IqVersionMixin(),
              entity_time.EntityTimeMixin(),
              presence.PresenceCacheMixin(),
              presence.SubscriptionAckMixin(),
             ]
    try:
        stream = yield from openConnection(Credentials(jid, password),
                                           host=jid.host, port=args.port,
                                           callbacks=Callbacks(), mixins=mixins,
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
    server_version = yield from iqversion.get(stream, jid.host)
    _outputXml(server_version)

    # Initial presence
    stream.send(Presence())

    if args.disconnect:
        stream.close()
        return 0

    while True:
        stanza = yield from stream.wait(("/*", None), timeout=None)
        _outputXml(stanza)

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

app = Application(main)
sys.exit(app.run())
