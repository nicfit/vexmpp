# -*- coding: utf-8 -*-
from lxml.etree import Element
from ..stanzas import XML_LANG
from ..utils import stripNsFromTag
from ..errors import XmppError

NS_URI = "urn:ietf:params:xml:ns:xmpp-sasl"


class SaslError(XmppError):
    '''
    Conditions: aborted, account-disabled, credentials-expired,
                encryption-required, incorrect-encoding, invalid-authzid,
                invalid-mechanism, mechanism-too-weak, not-authorized,
                temporary-auth-failure
    '''
    def __init__(self, cond=None, text=None, lang=None, xml=None):
        self.cond = cond
        self.text = text
        self.lang = lang

        if xml is not None:
            # 'xml' overrided and keyword args
            if xml.tag != "{%s}failure" % NS_URI:
                raise ValueError("'xml' is not a SASL error element")
            for child in list(xml):
                if child.tag == "text":
                    self.text = child.text
                    try:
                        self.lang = child.attrib[XML_LANG]
                    except KeyError:
                        pass
                else:
                    self.cond = stripNsFromTag(child.tag, NS_URI)

        if not self.cond:
            raise ValueError("Error condition 'cond' required")

    @property
    def xml(self):
        nsmap = {None: NS_URI}

        e = Element("{%s}failure" % NS_URI, nsmap=nsmap)
        e.append(Element("{%s}%s" % (NS_URI, self.cond), nsmap=nsmap))
        if self.text:
            txt = Element("{%s}text" % NS_URI, nsmap=nsmap)
            if self.lang:
                txt.attrib[XML_LANG] = self.lang
            txt.text = self.text
            e.append(txt)

        return e
