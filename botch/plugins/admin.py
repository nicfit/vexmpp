# -*- coding: utf-8 -*-
import asyncio
import logging
from io import StringIO
from pprint import pformat

from vexmpp.jid import Jid
from botch.app import ACL_GROUPS, CONFIG_SECT
from botch.plugin import command, ArgsParser, ArgsParserExitInfo

log = logging.getLogger("botch.plugins.admin")


ADMIN_CMD = "admin"
arg_parser = ArgsParser(description="Admin interface", prog=ADMIN_CMD)
subparsers = arg_parser.add_subparsers(dest="subcommand")

subparser = subparsers.add_parser("config")
subparser.add_argument("-s", "--save", action="store_true")

subparser = subparsers.add_parser("exit")


@command(ADMIN_CMD, acl="owner", arg_parser=arg_parser)
def _adminCommands(ctx):
    log.info("{} command invoked by {}".format(ctx.cmd, ctx.from_jid.full))

    subcmd = ctx.args.subcommand
    if subcmd is None:
        return ctx.arg_parser.format_usage()

    if subcmd == "config":
        config = ctx.bot.app.config
        def _readConfig():
            _fp = StringIO("w")
            config.write(_fp)
            _fp.seek(0)
            return _fp

        if ctx.args.save:
            # Update config with current ACL state
            ctx.bot._aclSave(config[CONFIG_SECT])

            config_file = ctx.bot.app.args.config_file
            with open(config_file, "w") as cf:
                cf.write(_readConfig().read())
            # XXX: comments are lost, bummer
            return "Config saved."
        else:
            # Show
            return _readConfig().read()
    elif subcmd == "exit":
        ctx.bot.app.stop(50)


arg_parser = ArgsParser(description="Access control lists interface",
                        prog="acl")
arg_parser.add_argument("-a", action="store", dest="add", default=None,
                        metavar="jid", type=Jid)
arg_parser.add_argument("-r", action="store", dest="remove", default=None,
                        metavar="jid", type=Jid)
arg_parser.add_argument("-g", action="store", choices=ACL_GROUPS,
                        dest="group", default="friend")

@command("acl", acl="owner", arg_parser=arg_parser)
def acl(ctx):
    msg = ""
    group = ctx.args.group
    a_jid = ctx.args.add
    r_jid = ctx.args.remove

    if a_jid:
        msg += "\nAdded '{}' to ACL {} group.".format(a_jid.bare, group)
        ctx.bot._acls[group].append(a_jid.bare_jid)
    if r_jid and r_jid.bare_jid in ctx.bot._acls[group]:
        msg += "\nRemoved '{}' to ACL {} group.".format(r_jid.bare, group)
        ctx.bot._acls[group].remove(r_jid.bare_jid)

    msg += "\n{}".format(pformat(ctx.bot._acls))
    return msg
