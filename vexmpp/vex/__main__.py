# -*- coding: utf-8 -*-
import os
import sys
import asyncio
import logging
from getpass import getpass

from nicfit.aio import Application
from nicfit.console import perr

import aiodns
import OpenSSL.SSL

from ..jid import Jid
from .. import version
from ..errors import XmppError
from ..stanzas import Presence
from ..protocols import iqversion, stream_mgmt
from ..client import (Credentials, DEFAULT_C2S_PORT, ClientStream,
                      ClientStreamCallbacks, TlsOpts)

from .util import _outputXml, _register, RegistrationError


async def main(args):
    if "VEX_PASSWD" in os.environ:
        password = os.environ["VEX_PASSWD"]
    else:
        password = getpass("Password for '%s': " % args.jid)
    jid = args.jid
    if not jid.resource:
        jid = Jid((jid.user, jid.host, "vex"))

    tls_opt = TlsOpts.fromString(args.tls)

    mixins = ClientStream.createDefaultMixins()
    if args.stream_mgmt:
        sm_opts = stream_mgmt.Opts()
        mixins.insert(0, stream_mgmt.Mixin(sm_opts))

    try:
        reg_cb = _register if args.register else None
        stream = await ClientStream.connect(Credentials(jid, password),
                                            host=args.host, port=args.port,
                                            state_callbacks=Callbacks(),
                                            tls_opt=tls_opt, mixins=mixins,
                                            register_cb=reg_cb, timeout=5)
    except asyncio.TimeoutError:
        print("Connection timed out", file=sys.stderr)
        return 1
    except XmppError as ex:
        print("XMPP error: %s" % str(ex), file=sys.stderr)
        return 2
    except OpenSSL.SSL.Error as ex:
        print("SSL error: %s" % str(ex), file=sys.stderr)
        return 3
    except aiodns.error.DNSError as ex:
        print("DNS resolution failure.", file=sys.stderr)
        return 5
    except RegistrationError as ex:
        print("Registration error:\n{}".format(ex), file=sys.stderr)
        return 6
    except ConnectionRefusedError as ex:
        print("Connection refused:\n{}".format(ex), file=sys.stderr)
        return 7

    # Server version
    server_version = await iqversion.get(stream, jid.host, timeout=10)
    _outputXml(server_version)

    # Initial presence
    stream.send(Presence())

    if args.disconnect:
        stream.close()
        return 0

    while True:
        try:
            stanza = await stream.wait(("/*", None), timeout=10)
            _outputXml(stanza)
        except asyncio.TimeoutError:
            pass

    return 0


class Callbacks(ClientStreamCallbacks):
    def disconnected(self, stream, reason):
        self._shutdown("Disconnected: {}".format(reason))

    def connectionFailed(self, host, port, reason):
        self._shutdown("Connection failed: {}".format(reason))

    def _shutdown(self, msg):
        global app
        perr(msg)
        app.event_loop.stop()

    def connecting(self, host, port):
        pass

    def sessionStarted(self, stream):
        pass

    def connected(self, stream, tls_active):
        pass

    def streamError(self, stream, error):
        self._shutdown("Stream error: {}".format(error))


about = "Simple XMPP client. The user will be prompted for a login password " \
        "unless the environment variable VEX_PASSWD is set."
app = Application(main, name="vex", description=about, version=version)
app.arg_parser.add_argument("jid", type=Jid, help="Jabber ID for login")
app.arg_parser.add_argument("--register", action="store_true",
                            help="Register for an account before logging in.")
app.arg_parser.add_argument("--host", help="Alternative server for connecting")
app.arg_parser.add_argument("--port", type=int, default=DEFAULT_C2S_PORT,
                            help="Alternative port for connecting")
app.arg_parser.add_argument("--disconnect", action="store_true",
                            help="Disconnect once stream negotiation "
                                 "completes.")
optgroup = app.arg_parser.add_argument_group("Stream feature options")
optgroup.add_argument("--tls", action="store",
                      default="on", choices=[e.name for e in TlsOpts],
                      help="TLS setting, 'on' by default.")
optgroup.add_argument("--stream-mgmt", action="store_true", default=False,
                      help="Enable stream management (XEP 198).")

logging.basicConfig()

if __name__ == "__main__":
    app.run()
