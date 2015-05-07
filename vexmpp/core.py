# -*- coding: utf-8 -*-
import asyncio
from . import client
from .protocols import iqroster, presence, iqversion, entity_time, disco


def mkDefaultMixins():
    return [
            iqroster.RosterMixin(),
            iqversion.IqVersionMixin(),
            entity_time.EntityTimeMixin(),
            presence.PresenceCacheMixin(),
            presence.SubscriptionAckMixin(),
            disco.DiscoCacheMixin(),
           ]


@asyncio.coroutine
def openConnection(creds, host=None, port=client.DEFAULT_C2S_PORT,
                   callbacks=None, mixins=None, timeout=None, loop=None):
    if not mixins:
        mixins = mkDefaultMixins()

    return (yield from client.openConnection(creds, host=host, port=port,
                                             callbacks=callbacks, mixins=mixins,
                                             timeout=timeout, loop=loop))
