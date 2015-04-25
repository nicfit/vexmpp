# -*- coding: utf-8 -*-
import sys
if sys.version_info[:3] < (3, 4, 2):
    raise RuntimeError("Python >= 3.4.2 required")


__projectname__ = 'vexmpp'
__author__ = 'Travis Shirk'
__email__ = 'travis@pobox.com'
__web__ = 'http://FIXME'

__version__ = '0.4.0'
__version_info__ = tuple((int(v) for v in __version__.split('.')))
__release__ = 'alpha'
__years__ = '2014'

__version_txt__ = """
%(__projectname__)s %(__version__)s-%(__release__)s (C) Copyright %(__author__)s
This program comes with ABSOLUTELY NO WARRANTY! See LICENSE for details.
Run with --help/-h for usage information or read the docs at
%(__web__)s
""" % (locals())

from . import log                                                        # noqa

from .jid import Jid                                                     # noqa
from . import stanzas                                                    # noqa
from . import client                                                     # noqa
