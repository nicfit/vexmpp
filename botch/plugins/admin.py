# -*- coding: utf-8 -*-
import asyncio
import logging
from io import StringIO
from pprint import pformat

from botch.plugin import Plugin, command

log = logging.getLogger("botch.plugins.admin")


@command(acl="owner")
def exit(env):
    log.critical("Botch asked to exit by {}".format(env.from_jid.bare))
    env.bot.app.stop(50)


@command([".config", ".acl"], acl="owner")
def _adminCommands(env):
    log.info("{} command invoked by {}".format(env.cmd, env.from_jid.full))

    if env.cmd == ".config":
        config = env.bot.app.config
        fp = StringIO("w")
        config.write(fp)
        fp.seek(0)
        return fp.read()
    elif env.cmd == ".acl":
        return "\n{}".format(pformat(env.bot._acls))
