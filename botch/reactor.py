# -*- coding: utf-8 -*-
import shlex
import asyncio
import logging

from vexmpp.protocols import muc
from .plugin import Plugin

log = logging.getLogger(__name__)


class Task(asyncio.Task):
    def __init__(self, config, bot, plugins, loop=None):
        self.bot = bot
        self.config = config

        self.plugins = {HelpPlugin: HelpPlugin(config, plugins)}
        self.plugins.update(plugins)
        self.commands = _extractCommands(self.plugins.values())

        super().__init__(self._run(), loop=loop)

    @asyncio.coroutine
    def _run(self):
        while True:
            try:
                log.debug("Reactor task waiting for stanza")
                stanza = yield from self.bot.wait(("/*", None), timeout=10)
            except asyncio.TimeoutError:
                continue

            if stanza.name == "message":
                self._handleMessage(stanza)

    def _handleMessage(self, msg):
        acl = self.bot.acl(msg.frm)
        log.info("Message [from: {} ({})]: {}" .format(msg.frm, acl, msg.body))

        if not self.bot.aclCheck(msg.frm, "other"):
            return

        if msg.type == "groupchat" or msg.x(muc. NS_URI_USER) is not None:
            muc_jid = muc.Jid(msg.frm)

            if (# Msg from the room...
                muc_jid.nick is None or # Msg from the room...
                # History msgs
                msg.x("jabber:x:delay") is not None or
                msg.find("{urn:xmpp:delay}delay") is not None or
                msg.x(muc.JINC_NS_URI_HISTORY) is not None
               ):
                return

        resp = None
        msg_parts = shlex.split(msg.body.strip())
        if msg_parts[0] in self.commands:
            # Command msg
            try:
                resp = self.commands[msg_parts[0]].callback(msg_parts[0],
                                                            msg.frm,
                                                            msg_parts[1:],
                                                            self.bot)
            except Exception:
                log.exception("Command error")
                return
        else:
            # Other msg
            resp = "Hi. Say {} for help".format(HelpPlugin.CMD)

        if resp:
            msg.body = resp
            msg.swapToFrom()
            self.bot.send(msg)


class HelpPlugin(Plugin):
    CMD = ".help"

    def __init__(self, config, plugins):
        super().__init__(config)

        self.addCommand(self.CMD, self._helpCmd)
        self._all_commands = _extractCommands(plugins.values())

    def _helpCmd(self, _, from_jid, args, bot):
        cmds = [c for c in self._all_commands.values()
                  if bot.aclCheck(from_jid, c.acl)]

        cmd_names = sorted([c.cmd for c in cmds])

        if not cmd_names:
            msg = "No commands"
        else:
            msg = ", ".join(cmd_names)
        return msg


def _extractCommands(plugins):
    commands = {}
    for p in plugins:
        # FIXME: detect name collisions
        commands.update(p.commands())
    return commands
