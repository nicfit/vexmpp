# -*- coding: utf-8 -*-
from lxml import etree
from nicfit.console import pout
try:
    from pygments import highlight
    from pygments.lexers import XmlLexer
    from pygments.formatters import TerminalFormatter
    _has_pygments = True
except:
    _has_pygments = False

from ..protocols import iqregister
from ..protocols.xdata import XdataForm


def _outputXml(stanza):
    xml = stanza.toXml(pprint=True, encoding="utf-8")
    if _has_pygments:
        xml = highlight(xml, XmlLexer(), TerminalFormatter())
    pout(xml)


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
        pout("{:^80}\n{hr:^80}".format(form.title, hr=("=" * len(form.title))))
    if form.instructions:
        pout("Instructions:\n\t{}\n".format(form.instructions))

    def _appendValue(elem, value_txt):
        value_elem = etree.Element("value")
        value_elem.text = value_txt
        elem.append(value_elem)

    for field in form.findall("{jabber:x:data}field"):
        var = field.get("var")
        value = field.find("{jabber:x:data}value")
        pout("{label} ({var}): {value}"
              .format(label=field.get("label"), var=var,
                      value=value.text if value else ""), end="")
        if not field.find("{jabber:x:data}value"):
            if var in ("username", "password"):
                _appendValue(field, creds.jid.user if var == "username"
                                                   else creds.password)
            else:
                resp = _prompt()
                form.setValue(var, resp)
        pout()
