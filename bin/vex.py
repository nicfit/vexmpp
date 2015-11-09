#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import asyncio
import logging.config
from io import StringIO
from getpass import getpass

import aiodns
import OpenSSL.SSL
from lxml import etree

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
from vexmpp.client import (Credentials, DEFAULT_C2S_PORT, ClientStream,
                           ClientStreamCallbacks, TlsOpts)
from vexmpp.stanzas import Presence
from vexmpp.protocols import iqversion, stream_mgmt, iqregister
from vexmpp.utils import ArgumentParser
from vexmpp import log


def _outputXml(stanza):
    xml = stanza.toXml(pprint=True, encoding="utf-8")
    if _has_pygments:
        xml = highlight(xml, XmlLexer(), TerminalFormatter())
    print(xml)


class RegistrationError(Exception):
    pass


def _register(creds, reg_query):
    def _appendValue(elem, value_txt):
        value_elem = etree.Element("value")
        value_elem.text = value_txt
        elem.append(value_elem)

    oob = reg_query.find("{jabber:x:oob}x")
    if oob is not None:
        inst = reg_query.find("{%s}instructions" % iqregister.NS_URI)
        url = oob.find("{jabber:x:oob}url")
        raise RegistrationError("{}\nurl: {}".format(inst.text, url.text))

    xdata = reg_query.find("{jabber:x:data}x")
    if xdata is not None:
        username = xdata.find("{jabber:x:data}field[@var='username']")
        _appendValue(username, creds.jid.user)

        password = xdata.find("{jabber:x:data}field[@var='password']")
        _appendValue(password, creds.password)

        title = xdata.find("{jabber:x:data}title")
        if title is not None:
            text = title.text
            print("{:^80}\n{hr:^80}".format(text, hr=("=" * len(text))))
        inst = xdata.find("{jabber:x:data}instructions")
        print("Instructions:\n\t{}\n".format(inst.text)
                if inst is not None else "", end="")
        for field in xdata.findall("{jabber:x:data}field"):
            if field.get("var") in ("username", "password"):
                continue

            print("{}: ".format(field.get("label") or field.get("var")),
                    end="")
            raise NotImplementedError()
    else:
        username = reg_query.find("{%s}username" % iqregister.NS_URI)
        username.text = creds.jid.user
        password = reg_query.find("{%s}password" % iqregister.NS_URI)
        password.text = creds.password


@asyncio.coroutine
def main(app):
    args = app.args

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
        stream = yield from ClientStream.connect(Credentials(jid, password),
                                                 host=args.host, port=args.port,
                                                 state_callbacks=Callbacks(),
                                                 tls_opt=tls_opt,
                                                 mixins=mixins,
                                                 register_cb=reg_cb,
                                                 timeout=5)
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
        self._shutdown("Disconnected: {}".format(reason))

    def connectionFailed(self, host, port, reason):
        self._shutdown("Connection failed: {}".format(reason))

    def _shutdown(self, msg):
        global app
        print(msg, file.sys.stderr)
        app.event_loop.stop()

    def connecting(self, host, port):
        pass

    def sessionStarted(self, stream):
        pass

    def connected(self, stream, tls_active):
        pass

    def streamError(self, stream, error):
        self._shutdown("Stream error: {}".format(error))


arg_parser = ArgumentParser(
    description="Simple XMPP client. The user will be prompted for a login "
                "password unless the environment variable VEX_PASSWD is set.")
arg_parser.add_argument("jid", type=Jid, help="Jabber ID for login")
arg_parser.add_argument("--register", action="store_true",
                        help="Register for an account before logging in.")
arg_parser.add_argument("--host", help="Alternative server for connecting")
arg_parser.add_argument("--port", type=int, default=DEFAULT_C2S_PORT,
                        help="Alternative port for connecting")
arg_parser.add_argument("--disconnect", action="store_true",
                        help="Disconnect once stream negotiation completes."
                       )
optgroup = arg_parser.add_argument_group("Stream feature options")
optgroup.add_argument("--tls", action="store",
                      default="on", choices=[e.name for e in TlsOpts],
                      help="TLS setting, 'on' by default.")
optgroup.add_argument("--stream-mgmt", action="store_true", default=False,
                      help="Enable stream management (XEP 198).")

log.addCommandLineArgs(arg_parser)
logging.config.fileConfig(StringIO(log.DEFAULT_FILE_CONFIG))

app = Application(main, argument_parser=arg_parser)
sys.exit(app.run())
