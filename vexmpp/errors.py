# -*- coding: utf-8 -*-
from lxml.etree import Element
from .namespaces import STREAM_NS_URI, STREAM_ERROR_NS_URI, STANZA_ERROR_NS_URI
from .stanzas import XML_LANG

'''
Concrete :class:StanzaError types.
    * BadRequestStanzaError
    * ConflictStanzaError
    * FetureNotImplementedStanzaError
    * ForbiddenStanzaError
    * GoneStanzaError
    * InternalServerErrorStanzaError
    * ItemNotFoundStanzaError
    * JidMalformedStanzaError
    * NotAcceptableStanzaError
    * NotAllowedStanzaError
    * NotAuthorizedStanzaError
    * PolicyViolationStanzaError
    * RecipientUnavailableStanzaError
    * RedirectStanzaError
    * RegistrationRequiredStanzaError
    * RemoteServerNotFoundStanzaError
    * RemoteServerTimeoutStanzaError
    * ResourceConstraintStanzaError
    * ServiceUnavailableStanzaError
    * SubscriptionRequiredStanzaError
    * UndefinedConditionStanzaError
    * UnexpectedRequestStanzaError


Concrete :code:StreamError types.
    * BadFormatStreamError
    * BadNamespacePrefixStreamError
    * ConflictStreamError
    * ConnectionTimeoutStreamError
    * HostGoneStreamError
    * HostUnknownStreamError
    * ImproperAddressingStreamError
    * InternalServerErrorStreamError
    * InvalidFromStreamError
    * InvalidNamespaceStreamError
    * InvalidXmlStreamError
    * NotAuthorizedStreamError
    * NotWellFormedStreamError
    * PolicyViolationStreamError
    * RemoteConnectionFailedStreamError
    * ResetStreamError
    * ResourceConstraintStreamError
    * RestrictedXmlStreamError
    * SeeOtherHostStreamError
    * SystemShutdownStreamError
    * UndefinedConditionStreamError
    * UnsupportedEncodingStreamError
    * UnsupportedFeatureStreamError
    * UnsupportedStanzaTypeStreamError
    * UnsupportedVersionStreamError
'''


class Error(RuntimeError):
    '''A generatl exception type for errors in the vexmpp domain.'''


TYPE_AUTH = "auth"
TYPE_CANCEL = "cancel"
TYPE_CONTINUE = "continue"
TYPE_MODIFY = "modify"
TYPE_WAIT = "wait"


# Tuple format (name, type, default-text, default_lang)
STANZA_ERRORS = (
    ("bad-request", TYPE_MODIFY, "", None),
    ("conflict", TYPE_CANCEL, "", None),
    ("feture-not-implemented", TYPE_CANCEL, "", None),
    ("forbidden", TYPE_AUTH, "", None),
    ("gone", TYPE_CANCEL, "", None),
    ("internal-server-error", TYPE_CANCEL, "", None),
    ("item-not-found", TYPE_CANCEL, "", None),
    ("jid-malformed", TYPE_MODIFY, "", None),
    ("not-acceptable", TYPE_MODIFY, "", None),
    ("not-allowed", TYPE_CANCEL, "", None),
    ("not-authorized", TYPE_AUTH, "", None),
    ("policy-violation", TYPE_MODIFY, "", None),
    ("recipient-unavailable", TYPE_WAIT, "", None),
    ("redirect", TYPE_MODIFY, "", None),
    ("registration-required", TYPE_AUTH, "", None),
    ("remote-server-not-found", TYPE_CANCEL, "", None),
    ("remote-server-timeout", TYPE_WAIT, "", None),
    ("resource-constraint", TYPE_WAIT, "", None),
    ("service-unavailable", TYPE_CANCEL, "", None),
    ("subscription-required", TYPE_AUTH, "", None),
    ("undefined-condition", TYPE_AUTH, "", None),
    ("unexpected-request", TYPE_WAIT, "", None),
)

# Tuple format (name, default-text, default_lang)
STREAM_ERRORS = (
    ("bad-format", "", None),
    ("bad-namespace-prefix", "", None),
    ("conflict", "", None),
    ("connection-timeout", "", None),
    ("host-gone", "", None),
    ("host-unknown", "", None),
    ("improper-addressing", "", None),
    ("internal-server-error", "", None),
    ("invalid-from", "", None),
    ("invalid-namespace", "", None),
    ("invalid-xml", "", None),
    ("not-authorized", "", None),
    ("not-well-formed", "", None),
    ("policy-violation", "", None),
    ("remote-connection-failed", "", None),
    ("reset", "", None),
    ("resource-constraint", "", None),
    ("restricted-xml", "", None),
    ("see-other-host", "", None),
    ("system-shutdown", "", None),
    ("undefined-condition", "", None),
    ("unsupported-encoding", "", None),
    ("unsupported-feature", "", None),
    ("unsupported-stanza-type", "", None),
    ("unsupported-version", "", None),
)


class XmppError(RuntimeError):
    '''An error for XMPP logic errors.'''
    cond = None
    text = None
    lang = None
    app_err = None

    def __str__(self):
        return "%s (text: %s [lang: %s]): %s" % (self.cond, self.text,
                                                 self.lang, self.app_err)


class StanzaError(XmppError):
    type = None

    def __init__(self):
        raise NotImplementedError("Instantiate a concrete error type")

    def __str__(self):
        return "%s (type: %s text: %s [lang: %s]): %s" % (self.cond, self.type,
                                                          self.text, self.lang,
                                                          self.app_err)

    @property
    def xml(self):
        assert(self.cond)

        e = Element("error")

        nsmap = {None: STANZA_ERROR_NS_URI}
        e.append(Element("{%s}%s" % (STANZA_ERROR_NS_URI, self.cond),
                         nsmap=nsmap))
        e[0].attrib["type"] = self.type
        if self.text:
            txt = Element("{%s}text" % STANZA_ERROR_NS_URI, nsmap=nsmap)
            if self.lang:
                txt.attrib[XML_LANG] = self.lang
            txt.text = self.text
            e.append(txt)

        if self.app_err:
            e.append(self.app_err)

        return e


class StreamError(XmppError):
    def __init__(self):
        raise NotImplementedError("Instantiate a concrete error type")

    @property
    def xml(self):
        assert(self.cond)

        e = Element("{%s}error" % STREAM_NS_URI,
                    nsmap={"stream": STREAM_NS_URI})

        nsmap = {None: STREAM_ERROR_NS_URI}
        e.append(Element("{%s}%s" % (STREAM_ERROR_NS_URI, self.cond),
                         nsmap=nsmap))
        if self.text:
            txt = Element("{%s}text" % STREAM_ERROR_NS_URI, nsmap=nsmap)
            if self.lang:
                txt.attrib[XML_LANG] = self.lang
            txt.text = self.text
            e.append(txt)

        if self.app_err:
            e.append(self.app_err)

        return e


def _makeClassName(cond, stanza_err):
    '''Simple util for turning stanza/stream error conditions into class
    names.'''
    class_name = ""
    next_leter_cap = True
    for c in cond:
        if next_leter_cap:
            assert(c != '-')
            c = c.upper()
            next_leter_cap = False
        elif c == '-':
            next_leter_cap = True
            continue
        class_name += c

    if stanza_err:
        return "%sStanzaError" % class_name
    else:
        return "%sStreamError" % class_name


# Make concrete error classes types for all the defined errors.
_global_dict = globals()
for _cond, _type, _txt, _lang in STANZA_ERRORS:
    _name = _makeClassName(_cond, True)

    def stanzaErrCtor(self, type=None, text=None, lang=None, app_err=None):
        # Use constructor values or defer to the Class vars
        self.type = type or self.__class__.type
        self.text = text or self.__class__.text
        self.lang = lang or self.__class__.lang
        self.app_err = app_err or self.__class__.app_err

    _global_dict[_name] = type(_name, (StanzaError,),
                               {"cond": _cond,
                               "type": _type,
                               "text": _txt,
                               "lang": _lang,
                               "app_err": None,
                               "__init__": stanzaErrCtor,
                               })
for _cond, _txt, _lang in STREAM_ERRORS:
    _name = _makeClassName(_cond, False)

    def streamErrCtor(self, text=None, lang=None, app_err=None):
        self.text = text or self.__class__.text
        self.lang = lang or self.__class__.lang
        self.app_err = app_err or self.__class__.app_err

    _global_dict[_name] = type(_name, (StreamError,),
                               {"cond": _cond,
                                "text": _txt,
                                "lang": _lang,
                                "app_err": None,
                                "__init__": streamErrCtor,
                               })
del _global_dict


##
# Make a concrete instance of \c StreamError based on \a xml.
#
# \param xml The &lt;stream:error&gt; Element
# \throws ValueError Thrown if \a xml is not a stream:error or lacks
#                    a condition.
# \returns A concrete instance of \c StreamError or
#          \c UndefinedConditionStreamError if the condition is not
#          recognozed.
def makeStreamError(xml):
    return _makeConcreteError(xml)


def makeStanzaError(xml):
    return _makeConcreteError(xml)


def _makeConcreteError(xml):
    stream_error, stanza_error = False, False
    if xml.xpath("/stream:error", namespaces={"stream": STREAM_NS_URI}):
        stream_error = True
        cond_tag_prefix = "{%s}" % STREAM_ERROR_NS_URI
    elif xml.tag == "error":
        stanza_error = True
        cond_tag_prefix = "{%s}" % STANZA_ERROR_NS_URI
    elif (xml.getchildren() and
            xml.getchildren()[0].tag.startswith("{%s}" % STANZA_ERROR_NS_URI)):
        # Many stream features will wrap a stranza error in a feature-specific
        # parent (xep 198, <failed>, e.g.).
        stanza_error = True
        cond_tag_prefix = "{%s}" % STANZA_ERROR_NS_URI
    else:
        raise ValueError("xml must be a stream:error or stanza error (no ns!)")

    cond, type_, text, lang, app_err = None, None, None, None, None
    for child in list(xml):
        if child.tag == "{%s}text" % STREAM_ERROR_NS_URI and child.text:
            text = child.text
            lang = child.attrib[XML_LANG] if XML_LANG in child.attrib \
                                          else None
        elif child.tag.startswith(cond_tag_prefix):
            cond = child
            if stanza_error and "type" in xml.attrib:
                type_ = xml.attrib["type"]
        else:
            app_err = child

    if cond is None:
        raise ValueError("No error condition in xml")

    if stream_error:
        cond = cond.tag[2 + len(STREAM_ERROR_NS_URI):]
    else:
        cond = cond.tag[2 + len(STANZA_ERROR_NS_URI):]
    Class = _makeClassName(cond, stanza_error)

    try:
        Class = globals()[Class]
    except KeyError:
        if stream_error:
            Class = globals()["UndefinedConditionStreamError"]
        else:
            Class = globals()["UndefinedConditionStanzaError"]

    if stream_error:
        return Class(text=text, lang=lang, app_err=app_err)
    else:
        return Class(type=type, text=text, lang=lang, app_err=app_err)
