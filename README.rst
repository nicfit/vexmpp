===============================
vexmpp
===============================

.. image:: https://badge.fury.io/py/vexmpp.png
    :target: http://badge.fury.io/py/vexmpp

.. image:: https://travis-ci.org/nicfit/vexmpp.png?branch=master
        :target: https://travis-ci.org/nicfit/vexmpp

.. image:: https://pypip.in/d/vexmpp/badge.png
        :target: https://pypi.python.org/pypi/vexmpp


XMPP for Python 3

* Free software: MIT license
* Documentation: https://vexmpp.readthedocs.org.

Features
--------

* TODO

Development Enviroment
----------------------

Create a virtual environment.

Virtualenv
~~~~~~~~~~
::
    $ virtualenv -p /usr/bin/python3 vexmpp-venv
    $ source vexmpp-venv/bin/activate
    (vexmpp-venv) $

Virtualenv-wrapper
~~~~~~~~~~~~~~~~~~
::
    $ mkvirtualenv -p /usr/bin/python3 vexmpp
    (vexmpp) $

Install required dependencies, and optional developer dependencies.::

    (vexmpp) $ pip install -r requirements.txt
    # Optional
    (vexmpp) $ pip install -r dev-requirements.txt

Set up development paths.::

    $ python setup.py develop
