# -*- coding: utf-8 -*-
from collections import namedtuple


__project_name__ = 'vexmpp'
__project_slug__ = 'vexmpp'
__author__ = 'Travis Shirk'
__author_email__ = 'travis@pobox.com'
__url__ = 'https://bitbucket.org/nicfit/vexmpp'
__description__ = 'XMPP for Python3'

__version__ = '0.4.0-alpha'
__release__ = __version__.split('-')[1] if '-' in __version__ else "final"
__version_info__ = \
    namedtuple("Version", "major, minor, maint, release")(
        *(tuple((int(v) for v in __version__.split('-')[0].split('.'))) +
          tuple((__release__,))))

__years__ = "2010-2016"
__license__ = 'GPL'

__version_txt__ = """
%(__name__)s %(__version__)s (C) Copyright %(__years__)s %(__author__)s
This program comes with ABSOLUTELY NO WARRANTY! See LICENSE for details.
Run with --help/-h for usage information or read the docs at
%(__url__)s
""" % (locals())

from nicfit import getLogger, rootLogger
log = rootLogger(__package__)
