# -*- coding: utf-8 -*-
import argparse
import configparser
from io import StringIO
from pathlib import Path

DEFAULT_CONFIG = None


class Config(configparser.ConfigParser):
    '''Class for storing, reading, and writing config.'''
    def __init__(self, filename, **kwargs):
        super().__init__(**kwargs)
        self.filename = Path(filename)


class ConfigFileType(argparse.FileType):
    '''ArgumentParser ``type`` for loading ``Config`` objects.'''
    def __init__(self, default_config=None, encoding="utf-8"):
        super().__init__(mode='r')
        self._encoding = encoding
        self._default_config = default_config

    def __call__(self, filename):
        try:
            fp = super().__call__(filename)
        except Exception as ex:
            if self._default_config:
                fp = StringIO(self._default_config)
            else:
                raise

        config = Config(filename)
        config.readfp(fp)

        return config


def addCommandLineArgs(arg_parser, required=False, default_file=None,
                       default_config=DEFAULT_CONFIG):
    group = arg_parser.add_argument_group("Configuration options")
    if required:
        arg_parser.add_argument("config", default=default_file,
                          help="Configuration file (ini file format).",
                          type=ConfigFileType(default_config=DEFAULT_CONFIG),
                          nargs="?" if default_file else None)
    else:
        group.add_argument("-c", "--config", dest="config",
                           metavar="FILENAME",
                           type=ConfigFileType(default_config=DEFAULT_CONFIG),
                           default=default_file,
                           help="Configuration file (ini file format).")

    # FIXME: implement the subs
    group.add_argument("-o", dest="config_overrides", action="append",
                       default=[], metavar="SECTION:OPTION=VALUE",
                       help="Overrides the values for configuration OPTION in "
                            "[SECTION].")
