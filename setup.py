#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from setuptools import setup


readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

requirements = [
    "lxml",
    "PyOpenSSL",
    "aiodns",
]

def find_packages(path, src):
    packages = []
    for pkg in [src]:
        for _dir, subdirectories, files in (
                os.walk(os.path.join(path, pkg))):
            if '__init__.py' in files:
                tokens = _dir.split(os.sep)[len(path.split(os.sep)):]
                packages.append(".".join(tokens))
    return packages

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='vexmpp',
    version='0.4.0',
    description='Annoying XMPP for Python 3',
    long_description=readme + '\n\n' + history,
    author='Travis Shirk',
    author_email='travis@pobox.com',
    url='https://bitbucket.org/nicfit/vexmpp',
    packages=find_packages('.','vexmpp'),
    package_dir={'vexmpp':
                 'vexmpp'},
    include_package_data=True,
    install_requires=requirements,
    license="GPL",
    zip_safe=False,
    keywords='vexmpp',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GPL License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='nose.collector',
    tests_require=test_requirements
)
