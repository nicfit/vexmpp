# -*- coding: utf-8 -*-
import base64
from lxml.etree import Element
from nicfit import getLogger

from .. import suelta
from ..protocols.sasl import SaslError, NS_URI


async def handle(stream, feature_elem, timeout=None):
    nsmap = {"sasl": NS_URI}

    server_mechs = []
    for mech_elem in feature_elem.xpath("//sasl:mechanism",
                                        namespaces=nsmap):
        server_mechs.append(mech_elem.text)

    def _tls_active():
        return stream.tls_active

    def _callback(mech, vals):
        log.debug("SASL _callback mech: %s values: %s" % (mech, vals))
        if "password" in vals:
            vals["password"] = stream.creds.password
        mech.fulfill(vals)

    def _secquery(mech, question):
        # FIXME: what is this?
        # import ipdb; ipdb.set_trace()
        return True

    # This could be set to a desired mech. From a config, for example.
    MECH = None
    sasl_engine = suelta.SASL(stream.creds.jid.host, "xmpp",
                              username=stream.creds.jid.user,
                              mech=MECH,
                              sec_query=_secquery,
                              tls_active=_tls_active,
                              request_values=_callback)
    sasl_mech = sasl_engine.choose_mechanism(server_mechs)

    auth = Element("{%s}auth" % NS_URI, nsmap={None: NS_URI})
    auth.attrib["mechanism"] = sasl_mech.name
    initial_resp = sasl_mech.process(None)
    if initial_resp:
        log.debug("initial_resp: %s" % str(initial_resp))
        auth.text = base64.b64encode(initial_resp)

    stream.send(auth)

    done = False
    while not done:
        resp = await stream.wait([("/sasl:success", nsmap),
                                  ("/sasl:failure", nsmap),
                                  ("/sasl:challenge", nsmap),
                                 ], timeout=timeout)
        if resp.xml.tag == "{%s}success" % NS_URI:
            done = True
            if resp.xml.text:
                # XXX: not really sure what to do with this
                log.debug("<success/> txt: %s" %
                          base64.b64decode(resp.xml.text))
        elif resp.xml.tag == "{%s}failure" % NS_URI:
            raise SaslError(xml=resp.xml)
        else:
            assert(resp.xml.tag == "{%s}challenge" % NS_URI)
            challenge = base64.b64decode(resp.xml.text.strip())
            log.debug("challenge: %s" % challenge)
            resp_txt = sasl_mech.process(challenge)
            auth = Element("{%s}response" % NS_URI, nsmap={None: NS_URI})
            if resp_txt:
                auth.text = base64.b64encode(resp_txt)
            stream.send(auth)


log = getLogger(__name__)
