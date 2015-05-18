# -*- coding: utf-8 -*-
import asyncio
import logging
from io import StringIO
from pprint import pformat

from botch.plugin import command, ArgsParser, ArgsParserExitInfo

log = logging.getLogger("botch.plugins.admin")


ADMIN_CMD = "admin"
arg_parser = ArgsParser(description="Admin interface", prog=ADMIN_CMD)
subparsers = arg_parser.add_subparsers(dest="subcommand")

subparser = subparsers.add_parser("config")

subparser = subparsers.add_parser("acl")

subparser = subparsers.add_parser("exit")


@command(ADMIN_CMD, acl="owner", arg_parser=arg_parser)
def _adminCommands(env):
    log.info("{} command invoked by {}".format(env.cmd, env.from_jid.full))

    subcmd = env.args.subcommand
    if subcmd is None:
        return env.arg_parser.format_usage()

    if subcmd == "config":
        config = env.bot.app.config
        fp = StringIO("w")
        config.write(fp)
        fp.seek(0)
        return fp.read()
    elif subcmd == "acl":
        return "\n{}".format(pformat(env.bot._acls))
    elif subcmd == "acl":
        env.bot.app.stop(50)
