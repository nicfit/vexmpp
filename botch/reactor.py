# -*- coding: utf-8 -*-
import shlex
import asyncio
import logging

from vexmpp.protocols import muc
from .plugin import (Plugin, command, all_commands, all_triggers,
                     CommandCtx, TriggerCtx, ArgsParser)

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
                if stanza.type == "groupchat":
                    yield from self._handleGroupchatMessage(stanza)
                else:
                    yield from self._handleMessage(stanza)

    @asyncio.coroutine
    def _handleGroupchatMessage(self, msg):
        assert(msg.type == "groupchat")
        muc_jid = muc.MucJid(msg.frm)
        self_jid = self.bot.muc_rooms[muc_jid.room_jid].self_jid

        # Stuff to ignore
        if (# Msg from the room...
            muc_jid.nick is None or
            # History msgs
            msg.x("jabber:x:delay") is not None or
            msg.find("{urn:xmpp:delay}delay") is not None or
            msg.x(muc.JINC_NS_URI_HISTORY) is not None
           ):
            return

        # "Triggers"
        if muc_jid != self_jid:
            # Swap addresses
            msg.to, msg.frm = muc_jid.room_jid, None

            for name in all_triggers:
                trigger = all_triggers[name]
                resp = None

                if not trigger.search:
                    match = trigger.regex.match(msg.body)
                else:
                    match = trigger.regex.findall(msg.body)

                if match:
                    try:
                        ctx = TriggerCtx(match=match, from_jid=muc_jid,
                                         stanza=msg, bot=self.bot)
                        resp = yield from trigger.callback(ctx)
                    except Exception:
                        log.exception("Trigger error")
                    else:
                        if resp:
                            msg.body = str(resp)
                            self.bot.send(msg)

    @asyncio.coroutine
    def _handleMessage(self, msg):
        global all_commands

        acl = self.bot.acl(msg.frm)
        log.info("Message [from: {} ({})]: {}" .format(msg.frm, acl, msg.body))

        if not self.bot.aclCheck(msg.frm, "other"):
            return

        # "Commands"
        resp = None
        msg_parts = shlex.split(msg.body.strip())
        if msg_parts[0] in all_commands:
            # Command msg
            cmd = all_commands[msg_parts[0]]
            try:
                ctx = CommandCtx(cmd=msg_parts[0], args=msg_parts[1:],
                                 from_jid=msg.frm, bot=self.bot,
                                 arg_parser=cmd.arg_parser,
                                 stanza=msg, acl=cmd.acl)
                resp = yield from all_commands[msg_parts[0]].callback(ctx)
            except Exception:
                log.exception("Command error")
                return
        else:
            # Other msg
            if self.bot.aclCheck(msg.frm, "friend"):
                resp = "``{}``'?".format(HELP_CMD)

        if resp:
            msg.body = str(resp)
            msg.swapToFrom()
            self.bot.send(msg)


HELP_CMD = "help"

@command(cmd=HELP_CMD)
def _helpCmd(ctx):
    global all_commands

    cmds = [c for c in all_commands.values()
              if ctx.bot.aclCheck(ctx.from_jid, c.acl)]

    cmd_names = sorted([c.cmd for c in cmds])
    if not cmd_names:
        msg = "Nothing to see here."
    else:
        msg = "Commands: " + ", ".join(cmd_names)
    return msg
