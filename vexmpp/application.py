# -*- coding: utf-8 -*-
import sys
import asyncio
import logging
import logging.config
from .utils import ArgumentParser

log = logging.getLogger(__name__)


class Application(object):

    def __init__(self, user_func=None, app_name=None, argument_parser=None):
        global log

        self.event_loop = asyncio.get_event_loop()
        self._entry_point = user_func if user_func else self._main
        self._exit_status = 0
        self.log = logging.getLogger(app_name) if app_name else log
        self.arg_parser = argument_parser or ArgumentParser()
        self.args = None

    @asyncio.coroutine
    def _main(self):
        '''Main entry point when constructed without a user function. Subclasses
        should implemented and return integer exit codes which will be the
        process exit value.'''
        log.warn("No user function defined.")
        return 0

    @asyncio.coroutine
    def _mainTask(self):
        log.debug("Application::_mainTask(): {}".format(sys.argv))

        self.args = self.arg_parser.parse_args()

        exit_status = 128
        try:
            if self._entry_point == self._main:
                exit_status = yield from self._entry_point()
            else:
                exit_status = yield from self._entry_point(self)
        except asyncio.CancelledError as ex:
            self._mainCancelled()
        except Exception as ex:
            if hasattr(self.args, "debug_pdb") and self.args.debug_pdb:
                try:
                    # Must delay the import of ipdb as say as possible because
                    # of https://github.com/gotcha/ipdb/issues/48
                    import ipdb as pdb
                except ImportError:
                    import pdb
                e, m, tb = sys.exc_info()
                pdb.post_mortem(tb)
            else:
                log.exception("Unhandled exception thrown from '%s': %s" %
                              (str(self._entry_point), str(ex)))
            exit_status = 254
        finally:
            exit_status = exit_status if exit_status is not None else 255
            log.debug("Application::_mainTask() returning %d" % exit_status)
            self.stop(exit_status)

    def _mainCancelled(self):
        '''If the _mainTask is cancelled this method is invoke. Subclasses can
        override to shutdown logic.'''
        log.warn("Cancelled")

    def run(self):
        log.debug("Application::run")

        self._main_task = self.event_loop.create_task(self._mainTask())

        try:
            self.event_loop.run_until_complete(self._main_task)
        except KeyboardInterrupt:
            log.warn("Interrupted")
            self._main_task.cancel()

        log.debug("Application::run returning %d" % self._exit_status)
        return self._exit_status

    def stop(self, exit_status=0):
        log.debug("Application::stop(exit_status=%d)" % exit_status)

        self._exit_status = exit_status
        self.event_loop.stop()
        logging.shutdown()
