#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
from setuptools import setup, find_packages


classifiers = [
    'Development Status :: 2 - Pre-Alpha',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GPL License',
    'Operating System :: POSIX',
    'Natural Language :: English',
    'Programming Language :: Python',
    "Programming Language :: Python :: 2",
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
]


def getPackageInfo():
    info_dict = {}
    info_keys = ["version", "name", "author", "author_email", "url", "license",
                 "description"]

    base = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(base, "vexmpp/__init__.py")) as infof:
        for line in infof:
            for what in info_keys:
                rex = re.compile(r"__{what}__\s*=\s*['\"](.*?)['\"]"
                                  .format(what=what))

                m = rex.match(line.strip())
                if not m:
                    continue
                info_dict[what] = m.groups()[0]

    return info_dict


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

def requirements(filename):
    return open('requirements/' + filename).read().splitlines()


pkg_info = getPackageInfo()

src_dist_tgz = "{name}-{version}.tar.gz".format(**pkg_info)
pkg_info["download_url"] = "{}/releases/{}".format(pkg_info["url"],
                                                   src_dist_tgz)

setup(classifiers=classifiers,
      package_dir={'vexmpp': 'vexmpp'},
      packages=find_packages('.','vexmpp'),
      zip_safe=False,
      platforms=["Any",],
      keywords=['vexmpp'],
      include_package_data=True,
      install_requires=requirements("default.txt"),
      tests_require=requirements("test.txt"),
      test_suite='tests',
      long_description=readme + '\n\n' + history,
      package_data={},
      **pkg_info
)
