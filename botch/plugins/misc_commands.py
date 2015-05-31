# -*- coding: utf-8 -*-
from botch.plugin import command


@command()
def whoami(env):
    return env.from_jid.full


@command(acl="owner")
def loglevel(ctx):
    '''Change bot's logging level.'''
    from vexmpp.log import LEVEL_NAMES, optLoggerFile, optLoggerLevel

    if ctx.args:
        try:
            optLoggerLevel(ctx.args.pop())
            return "Done"
        except AttributeError:
            return "Valid levels: " + ",".join(LEVEL_NAMES)
