# -*- coding: utf-8 -*-
from vexmpp.stanzas import Presence
from botch.plugin import command, ArgsParser, ArgsParserExitInfo

PRES_CMD = "presence"
pres_parser = ArgsParser(description="Presence interface", prog=PRES_CMD)
pres_subparsers = pres_parser.add_subparsers(dest="subcommand")

subparser = pres_subparsers.add_parser("status")
subparser.add_argument("status", metavar="<text>",
                       help="The status message text.")

subparser = pres_subparsers.add_parser("priority")
subparser.add_argument("priority", type=int, metavar="N",
                       help="priority value -128 < N < 127")

subparser = pres_subparsers.add_parser("show")
subparser.add_argument("show",
                       choices=[str(s) for s in Presence.ORDERED_SHOWS],
                       help="Set the show state.")

@command(PRES_CMD, acl="owner", arg_parser=pres_parser)
def presence(env):
    subcmd = env.args.subcommand
    curr = env.bot.presence_cache.self
    args = env.args

    if subcmd is None:
        return curr.toXml(pprint=True).decode("utf8")

    try:
        if subcmd == "status":
            env.bot.sendPresence(status=args.status, priority=curr.priority,
                                 show=curr.show)
        elif subcmd == "priority":
            env.bot.sendPresence(status=curr.status, priority=args.priority,
                                 show=curr.show)
        elif subcmd == "show":
            if args.show == "None":
                args.show = None
            env.bot.sendPresence(status=curr.status, priority=curr.priority,
                                 show=args.show)
    except Exception as ex:
        return "Error: {}".format(ex)
