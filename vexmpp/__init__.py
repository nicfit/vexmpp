from nicfit import getLogger
from .__about__ import __version__ as version
from .jid import Jid
from .client import ClientStream, Credentials

__all__ = ["Jid", "ClientStream", "Credentials", "version"]
log = getLogger(__package__)
