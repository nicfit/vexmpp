# -*- coding: utf-8 -*-
import asyncio
import logging
from io import StringIO
from pprint import pformat

from botch.plugin import Plugin

log = logging.getLogger("botch.plugins.admin")


class AdminPlugin(Plugin):

    def __init__(self, config):
        super().__init__(config)
        self.addCommand(".exit", _adminCmd, "owner")
        self.addCommand(".config", _adminCmd, "owner")
        self.addCommand(".acl", _adminCmd, "owner")


def _adminCmd(cmd, from_jid, args, bot):
    log.info("{} command invoked by {}".format(cmd, from_jid.full))

    if cmd == ".exit":
        log.critical("Botch exiting...")
        bot.app.stop(50)
    elif cmd == ".config":
        config = bot.app.config
        fp = StringIO("w")
        config.write(fp)
        fp.seek(0)
        return fp.read()
    elif cmd == ".acl":
        return "\n{}".format(pformat(bot._acl))
