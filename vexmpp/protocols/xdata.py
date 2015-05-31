# -*- coding: utf-8 -*-
from ..stanzas import ElementWrapper

NS_URI = "jabber:x:data"


class XdataForm(ElementWrapper):
    '''XEP-0004'''

    def __init__(self, xml=None):
        if xml:
            if xml.tag != "{%s}x" % NS_URI:
                raise ValueError("xml is not x-data")
        else:
            from lxml import etree
            xml = etree.Element("{%s}x" % NS_URI, nsmap={None: NS_URI})
            xml.set("type", "form")

        super().__init__(xml)

    def _tagname(self, tag):
        return self._makeTagName(tag, NS_URI)

    @property
    def title(self):
        self._getChildText(_tagname("title"))

    @title.setter
    def title(self, t):
        self._setChildText(self._makeTagName("title"), t)

    @property
    def instructions(self):
        self._getChildText(self._makeTagName("instructions"))

    @instructions.setter
    def instructions(self, t):
        self._setChildText(self._makeTagName("instructions"), t)

    def field(self, var):
        return self.find("./{field}[@var='{var}']"
                         .format(var=var, field=self._tagname("field")))

    def appendListField(self, var, options, default=None, multi=False):
        assert(var)
        if default and default not in options:
            raise ValueError("Default value '{}' not in options."
                             .format(default))

        f = self.appendChild("field")
        f.attrib["var"] = var
        f.attrib["type"] = "list-single" if not multi else "list-multi"
        if default:
            f.appendChild("value").text = default
        for val in options:
            f.appendChild("option").appendChild("value").text = val

        return f
