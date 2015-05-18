# -*- coding: utf-8 -*-
from botch.plugin import command


@command()
def whoami(env):
    return env.from_jid.full


