# -*- coding: utf-8 -*-
from collections import namedtuple


__project_name__ = 'vexmpp'
__project_slug__ = 'vexmpp'
__author__ = 'Travis Shirk'
__author_email__ = 'travis@pobox.com'
__url__ = 'http://example.com/...'
__description__ = 'Asyncio XMPP'

__version__ = '0.1.0-alpha'
__release__ = __version__.split('-')[1] if '-' in __version__ else "final"
__version_info__   = \
    namedtuple("Version", "major, minor, maint, release")(
        *(tuple((int(v) for v in __version__.split('-')[0].split('.'))) +
          tuple((__release__,))))

__years__ = '2015'
__license__ = 'GPL'

__version_txt__ = """
%(__name__)s %(__version__)s (C) Copyright %(__author__)s
This program comes with ABSOLUTELY NO WARRANTY! See LICENSE for details.
Run with --help/-h for usage information or read the docs at
%(__url__)s
""" % (locals())

from . import log                                                        # noqa

from .jid import Jid                                                     # noqa
from . import stanzas                                                    # noqa
from . import client                                                     # noqa
