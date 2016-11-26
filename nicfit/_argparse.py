# -*- coding: utf-8 -*-
import argparse
import logging
from io import StringIO
from os.path import expandvars, expanduser

from ._logging import LEVEL_NAMES, LogFileAction, LogLevelAction


class ArgumentParser(argparse.ArgumentParser):
    """
    TODO
    """

    def __init__(self, add_log_args=True, config_opts=None, **kwargs):
        self._config_opts = config_opts

        super().__init__(**kwargs)

        if add_log_args:
            self.register("action", "log_levels", LogLevelAction)
            self.register("action", "log_files", LogFileAction)

            group = self.add_argument_group("Logging options")
            group.add_argument(
                "-l", "--log-level", dest="log_levels",
                action="log_levels", metavar="LOGGER:LEVEL", default=[],
                help="Set logging levels (the option may be specified multiple "
                     "times). The level of a specific logger may be set with "
                     "the syntax LOGGER:LEVEL, but LOGGER is optional so "
                     "if only LEVEL is given it applies to the root logger. "
                     "Valid level names are: %s" % ", ".join(LEVEL_NAMES))

            group.add_argument(
                "-L", "--log-file", dest="log_files",
                action="log_files", metavar="LOGGER:FILE", default=[],
                help="Set log files (the option may be specified multiple "
                     "times). The level of a specific logger may be set with "
                     "the syntax LOGGER:FILE, but LOGGER is optional so "
                     "if only FILE is given it applies to the root logger. "
                     "The special FILE values 'stdout', 'stderr', and 'null' "
                     "result on logging to the console, or /dev/null in the "
                     "latter case.")

        if config_opts:
            group = self.add_argument_group("Configuration options")
            file_arg_type = ConfigFileType(config_opts)

            if config_opts.required:
                self.add_argument("config", default=config_opts.default_file,
                                  help="Configuration file (ini file format).",
                                  type=file_arg_type,
                                  nargs="?" if config_opts.default_file
                                            else None)
            else:
                group.add_argument("-c", "--config", dest="config",
                                   metavar="FILENAME",
                                   type=file_arg_type,
                                   default=config_opts.default_file,
                                   help="Configuration file (ini file format).")

            group.add_argument("--config-override", dest="config_overrides",
                               action="append", default=[],
                               metavar="SECTION:OPTION=VALUE",
                               type=config_override,
                               help="Overrides the values for configuration "
                                    "OPTION in [SECTION].")

    def parse_known_args(self, args=None, namespace=None):
        parsed, remaining = super().parse_known_args(args=args,
                                                     namespace=namespace)
        if "config" in parsed and "config_overrides" in parsed:
            config = parsed.config
            for sect, subst in parsed.config_overrides:
                key, val = subst
                if not config.has_section(sect):
                    config.add_section(sect)
                parsed.config.set(sect, key, val)

        if "config" in parsed:
            logging.config.fileConfig(parsed.config)

        return parsed, remaining


class ConfigFileType(argparse.FileType):
    '''ArgumentParser ``type`` for loading ``Config`` objects.'''
    def __init__(self, config_opts):
        super().__init__(mode='r')
        self._opts = config_opts

    def __call__(self, filename):
        try:
            fp = super().__call__(expandvars(expanduser(filename)))
        except Exception as ex:
            if self._opts.default_config:
                fp = StringIO(self._opts.default_config)
            else:
                raise

        config = self._opts.ConfigClass(filename)
        config.readfp(fp)

        return config


def config_override(s):
    sect, rhs = s.split(':', 1)
    key, val = rhs.split('=', 1)
    return (sect, (key, val))


    if ':' in opt:
        first, second = opt.split(":")
    else:
        first, second = None, opt
    return first, second
