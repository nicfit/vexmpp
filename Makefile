.PHONY: clean-pyc clean-build clean-patch docs clean help lint test test-all \
        coverage docs release dist tags
SRC_DIRS = vexmpp tests bin botch
define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "clean-patch - remove patch artifacts (.rej, .orig)"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "release - package and upload a release"
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"

clean: clean-build clean-pyc clean-test clean-patch
	rm -rf tags

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage

clean-patch:
	find . -name '*.rej' -exec rm -f '{}' \;
	find . -name '*.orig' -exec rm -f '{}' \;

lint:
	flake8 ${SRC_DIRS}


_NOSE_OPTS=--verbosity=1 --detailed-errors
ifdef TEST_PDB
    _PDB_OPTS=--pdb --pdb-failures -s
endif
test:
	nosetests $(_NOSE_OPTS) $(_PDB_OPTS)

test-all:
	tox

_COVERAGE_BUILD_D=build/tests/coverage
coverage:
	nosetests $(_NOSE_OPTS) $(_PDB_OPTS) --with-coverage \
	          --cover-erase --cover-tests --cover-inclusive \
		  --cover-package=vexmpp \
		  --cover-branches --cover-html \
		  --cover-html-dir=$(_COVERAGE_BUILD_D) tests
	$(BROWSER) $(_COVERAGE_BUILD_D)/index.html

docs:
	rm -f docs/vexmpp.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ vexmpp
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

servedocs: docs
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: clean
	python setup.py sdist upload
	python setup.py bdist_wheel upload

dist: clean
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean
	python setup.py install

tags:
	ctags -R ${SRC_DIRS}
