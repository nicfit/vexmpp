# -*- coding: utf-8 -*-
from ..stanzas import ElementWrapper

NS_URI = "jabber:x:data"


class XdataForm(ElementWrapper):
    '''XEP-0004'''

    def __init__(self, xml=None):
        if xml is not None:
            if xml.tag != "{%s}x" % NS_URI:
                raise ValueError("xml is not x-data")
        else:
            from lxml import etree
            xml = etree.Element("{%s}x" % NS_URI, nsmap={None: NS_URI})
            xml.set("type", "form")

        super().__init__(xml)

    @property
    def title(self):
        self._getChildText("title")

    @title.setter
    def title(self, t):
        self._setChildText("title", t)

    @property
    def instructions(self):
        self._getChildText("instructions")

    @instructions.setter
    def instructions(self, t):
        self._setChildText("instructions", t)

    def field(self, var):
        return self.find("./{field}[@var='{var}']"
                         .format(var=var, field=self._makeTagName("field",
                                                                  NS_URI)))

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

    def setValue(self, field, val):
        self.field(field)._setChildText("value", val)
