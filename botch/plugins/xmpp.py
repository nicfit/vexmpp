# -*- coding: utf-8 -*-
from vexmpp.jid import Jid
from vexmpp.stanzas import Presence, Message
from botch.plugin import command, ArgsParser, ArgsParserExitInfo


PRES_CMD = "presence"
arg_parser = ArgsParser(description="Presence interface", prog=PRES_CMD)
subparsers = arg_parser.add_subparsers(dest="subcommand")

sub1 = subparsers.add_parser("status")
sub1.add_argument("status", metavar="<text>",
                       help="The status message text.")

sub2 = subparsers.add_parser("priority")
sub2.add_argument("priority", type=int, metavar="N",
                  help="priority value -128 < N < 127")

sub3 = subparsers.add_parser("show")
sub3.add_argument("show", choices=[str(s) for s in Presence.ORDERED_SHOWS],
                  help="Set the show state.")


@command(PRES_CMD, acl="owner", arg_parser=arg_parser)
def presence(ctx):
    subcmd = ctx.args.subcommand
    curr = ctx.bot.presence_cache.self
    args = ctx.args
    bot = ctx.bot

    if subcmd is None:
        return curr.toXml(pprint=True).decode("utf8")

    try:
        if subcmd == "status":
            bot.sendPresence(status=args.status, priority=curr.priority,
                             show=curr.show)
        elif subcmd == "priority":
            bot.sendPresence(status=curr.status, priority=args.priority,
                             show=curr.show)
        elif subcmd == "show":
            if args.show == "None":
                args.show = None
            bot.sendPresence(status=curr.status, priority=curr.priority,
                             show=args.show)
    except Exception as ex:
        return "Error: {}".format(ex)


MSG_CMD = "msg"
arg_parser = ArgsParser(description="Message interface", prog=MSG_CMD)
arg_parser.add_argument("jid", type=Jid, metavar="user@host")
arg_parser.add_argument("msg", metavar="<msg text ...>", nargs='+')
@command(MSG_CMD, acl="owner", arg_parser=arg_parser)
def msg(ctx):
    msg_text = " ".join(ctx.args.msg)
    m = Message(to=ctx.args.jid, body=msg_text)
    ctx.bot.send(m)
