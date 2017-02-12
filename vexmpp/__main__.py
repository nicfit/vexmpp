# -*- coding: utf-8 -*-
from nicfit.aio import Application
from nicfit.console import pout
from . import version


async def main(args):
    pout("\m/")


app = Application(main, version=version,
                  gettext_domain=None)

if __name__ == "__main__":
    app.run()
