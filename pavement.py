# -*- coding: utf-8 -*-
import os
import re
from paver.easy import *
from paver.path import path


def _setup(args, capture=False):
    return sh("python setup.py %s 2> /dev/null" % args, capture=capture)


NAME, VERSION, AUTHOR, *_ = _setup("--name --version --author",
                                   capture=True).split('\n')
FULL_NAME = '-'.join([NAME, VERSION])
SRC_DIRS = ["vexmpp", "tests", "bin"]

options(
    test=Bunch(
        pdb=False,
        coverage=False,
    ),
)

## -- misc tasks -- ##

@task
def lint():
    sh('flake8 {}'.format(" ".join(SRC_DIRS)))


## -- test tasks -- ##


@task
@cmdopts([("pdb", "",
           u"Run with all output and launch pdb on errors and failures"),
          ("coverage", "", u"Run tests with coverage analysis"),
         ])
def test(options):
    if options.test and options.test.pdb:
        debug_opts = "--pdb --pdb-failures -s"
    else:
        debug_opts = ""

    coverage_build_d = "build/tests/coverage"
    if options.test and options.test.coverage:
        coverage_opts = (
            "--cover-erase --with-coverage --cover-tests --cover-inclusive "
            "--cover-package=vexmpp --cover-branches --cover-html "
            "--cover-html-dir=%s tests" % coverage_build_d)
    else:
        coverage_opts = ""

    sh("nosetests --verbosity=1 --detailed-errors "
       "%(debug_opts)s %(coverage_opts)s" %
       {"debug_opts": debug_opts, "coverage_opts": coverage_opts})

    if coverage_opts:
        report = "%s/%s/index.html" % (os.getcwd(), coverage_build_d)
        print("Coverage Report: file://%s" % report)
        _browser(report)


@task
def test_all():
    '''Run tests for all Python versions.'''
    sh("tox")


## -- clean tasks -- ##

@task
def clean_build():
    sh("rm -fr build/")
    sh("rm -fr dist/")
    sh("rm -fr .eggs/")
    sh("find . -name '*.egg-info' -exec rm -fr {} +")
    sh("find . -name '*.egg' -exec rm -f {} +")


@task
def clean_pyc():
    sh("find . -name '*.pyc' -exec rm -f {} +")
    sh("find . -name '*.pyo' -exec rm -f {} +")
    sh("find . -name '*~' -exec rm -f {} +")
    sh("find . -name '__pycache__' -exec rm -fr {} +")


@task
def clean_test():
    sh("rm -fr .tox/")
    sh("rm -f .coverage")
    sh("rm -fr htmlcov/")


@task
def clean_patch():
    sh("find . -name '*.rej' -exec rm -f '{}' \;")
    sh("find . -name '*.orig' -exec rm -f '{}' \;")


@task
@needs("clean_build", "clean_pyc", "clean_test", "clean_patch")
def clean():
    sh("rm -fr htmlcov/")
    sh("rm -rf tags")


## -- dist tasks -- ##


@task
@needs("clean")
def dist():
    _setup("sdist")
    _setup("bdist_wheel")
    sh("ls -l dist")


# TODO
# docs
# servedocs
# release
# install
# lint
# help



## -- utils -- ##


def  _browser(file_path):
    import webbrowser
    try:
            from urllib import pathname2url
    except:
            from urllib.request import pathname2url

    webbrowser.open("file://" + pathname2url(os.path.abspath(file_path)))


## -- cookiecutter -- ##
@task
def cookiecutter():
    from cookiecutter.main import cookiecutter
    cookiecutter("https://bitbucket.org/nicfit/cookiecutter-pypackage",
                 extra_context={'_comment': '##### end #####',
 'asyncio': 'yes',
 'bitbucket_username': 'nicfit',
 'config_mod': 'yes',
 'email': 'travis@pobox.com',
 'full_name': 'Travis Shirk',
 'github_username': 'nicfit',
 'license': 'GPL',
 'log_mod': 'yes',
 'project_name': 'vexmpp',
 'project_short_description': 'XMPP for Python3',
 'project_slug': 'vexmpp',
 'py_module': 'vexmpp',
 'pypi_username': 'nicfit',
 'release_date': 'today',
 'support_python2': 'no',
 'support_python3': 'yes',
 'use_bitbucket': 'yes',
 'use_github': 'yes',
 'use_make': 'yes',
 'use_paver': 'yes',
 'use_pypi_deployment_with_travis': 'no',
 'version': '0.1.0-alpha',
 'web': 'https://bitbucket.org/nicfit/vexmpp',
 'year': '2010-2016'},
                 output_dir="..", no_input=True, overwrite_if_exists=True)


