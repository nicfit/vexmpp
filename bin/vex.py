#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import asyncio
from getpass import getpass

import aiodns
import OpenSSL.SSL
from lxml import etree
from nicfit import ArgumentParser, LOGGING_CONFIG
from nicfit.aio import Application

try:
    from pygments import highlight
    from pygments.lexers import XmlLexer
    from pygments.formatters import TerminalFormatter
    _has_pygments = True
except:
    _has_pygments = False

import vexmpp
from vexmpp.jid import Jid
from vexmpp.errors import XmppError
from vexmpp.client import (Credentials, DEFAULT_C2S_PORT, ClientStream,
                           ClientStreamCallbacks, TlsOpts)
from vexmpp.stanzas import Presence
from vexmpp.protocols.xdata import XdataForm
from vexmpp.protocols import iqversion, stream_mgmt, iqregister


def _outputXml(stanza):
    xml = stanza.toXml(pprint=True, encoding="utf-8")
    if _has_pygments:
        xml = highlight(xml, XmlLexer(), TerminalFormatter())
    print(xml)


class RegistrationError(Exception):
    pass


def _register(creds, reg_query):
    oob = reg_query.find("{jabber:x:oob}x")
    if oob is not None:
        inst = reg_query.find("{%s}instructions" % iqregister.NS_URI)
        url = oob.find("{jabber:x:oob}url")
        raise RegistrationError("{}\nurl: {}".format(inst.text, url.text))

    xdata = reg_query.find("{jabber:x:data}x")
    if xdata is not None:
        form = XdataForm(xml=xdata.xml)
        getXData(form, creds)
    else:
        username = reg_query.find("{%s}username" % iqregister.NS_URI)
        username.text = creds.jid.user
        password = reg_query.find("{%s}password" % iqregister.NS_URI)
        password.text = creds.password


def getXData(form, creds):
    def _prompt(txt=None):
        if txt:
            return input("{txt}: ".format(**locals()))
        else:
            return input()

    if form.title:
        print("{:^80}\n{hr:^80}".format(form.title, hr=("=" * len(form.title))))
    if form.instructions:
        print("Instructions:\n\t{}\n".format(form.instructions))

    def _appendValue(elem, value_txt):
        value_elem = etree.Element("value")
        value_elem.text = value_txt
        elem.append(value_elem)

    for field in form.findall("{jabber:x:data}field"):
        var = field.get("var")
        value = field.find("{jabber:x:data}value")
        print("{label} ({var}): {value}"
              .format(label=field.get("label"), var=var,
                      value=value.text if value else ""), end="")
        if not field.find("{jabber:x:data}value"):
            if var in ("username", "password"):
                _appendValue(field, creds.jid.user if var == "username"
                                                   else creds.password)
            else:
                resp = _prompt()
                form.setValue(var, resp)
        print()


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


about = "Simple XMPP client. The user will be prompted for a login password " \
        "unless the environment variable VEX_PASSWD is set."
app = Application(main, name="vex", description=about,
                  version=vexmpp.__version__)
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

LOGGING_CONFIG("vexmpp", init_logging=True)
app.run()
