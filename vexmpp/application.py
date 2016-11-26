# -*- coding: utf-8 -*-
import sys
import asyncio
from nicfit import ArgumentParser

from . import getLogger
log = getLogger(__name__)


class Application(object):

    def __init__(self, user_func=None, app_name=None, argument_parser=None):
        global log

        self.event_loop = asyncio.get_event_loop()
        self._entry_point = user_func if user_func else self._main
        self._exit_status = 0
        self.log = getLogger(app_name) if app_name else log
        self.arg_parser = argument_parser or ArgumentParser(prog=app_name)
        self.args = None

    async def _main(self):
        '''Main entry point when constructed without a user function. Subclasses
        should implemented and return integer exit codes which will be the
        process exit value.'''
        log.warn("No user function defined.")
        return 0

    async def _mainTask(self):
        log.debug("Application::_mainTask(): {}".format(sys.argv))

        self.args = self.arg_parser.parse_args()

        exit_status = None
        if self._entry_point == self._main:
            exit_status = await self._entry_point()
        else:
            exit_status = await self._entry_point(self)
        return exit_status

    def run(self):
        log.debug("Application::run")

        self._main_task = self.event_loop.create_task(self._mainTask())

        try:
            self._exit_status = self.event_loop\
                                    .run_until_complete(self._main_task)
        except KeyboardInterrupt:
            log.debug("Interrupted")
            self._exit_status = 0
        except asyncio.CancelledError as ex:
            log.debug("Cancelled")
        except Exception as ex:
            log.exception("Unhandled exception thrown from '%s': %s" %
                          (str(self._entry_point), str(ex)))
            if hasattr(self.args, "debug_pdb") and self.args.debug_pdb:
                try:
                    # Must delay the import of ipdb as say as possible because
                    # of https://github.com/gotcha/ipdb/issues/48
                    import ipdb as pdb
                except ImportError:
                    import pdb
                e, m, tb = sys.exc_info()
                pdb.post_mortem(tb)

            self._exit_status = 254

        log.debug("Application::run returning %d" % self._exit_status)
        return self._exit_status if self. _exit_status is not None else 255

    def stop(self, exit_status=0):
        log.debug("Application::stop(exit_status=%d)" % exit_status)
        self._exit_status = exit_status
        self._main_task.cancel()
