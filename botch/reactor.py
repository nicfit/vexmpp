# -*- coding: utf-8 -*-
import shlex
import asyncio
import logging

from vexmpp.protocols import muc
from .plugin import Plugin, command, all_commands, CommandEnv

log = logging.getLogger(__name__)


class Task(asyncio.Task):
    def __init__(self, config, bot, plugins, loop=None):
        self.bot = bot
        self.config = config

        self.plugins = {}
        self.plugins.update(plugins)

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
        global all_commands

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
        if msg_parts[0] in all_commands:
            # Command msg
            cmd = all_commands[msg_parts[0]]
            try:
                env = CommandEnv(cmd=msg_parts[0], args=msg_parts[1:],
                                 from_jid=msg.frm, bot=self.bot,
                                 arg_parser=cmd.arg_parser)
                resp = all_commands[msg_parts[0]].callback(env)
            except Exception:
                log.exception("Command error")
                return
        else:
            # Other msg
            if self.bot.aclCheck(msg.frm, "friend"):
                resp = "{} for help".format("/".join(HELP_CMDS))

        if resp:
            msg.body = str(resp)
            msg.swapToFrom()
            self.bot.send(msg)


HELP_CMDS = ("-h", "--help")

@command(cmd=HELP_CMDS)
def _helpCmd(env):
    global all_commands

    cmds = [c for c in all_commands.values()
              if env.bot.aclCheck(env.from_jid, c.acl)]

    cmd_names = sorted([c.cmd for c in cmds])
    if not cmd_names:
        msg = "Nothing to see here."
    else:
        msg = "Commands: " + ", ".join(cmd_names)
    return msg
