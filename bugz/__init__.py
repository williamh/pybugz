#!/usr/bin/env python

"""
Python Bugzilla Interface

Simple command-line interface to bugzilla to allow:
 - searching
 - getting bug info
 - saving attachments

Requirements
------------
 - Python 2.5 or later

Classes
-------
 - Bugz - Pythonic interface to Bugzilla
 - PrettyBugz - Command line interface to Bugzilla

"""

__version__ = '0.9.3'
__author__ = 'Alastair Tse <http://www.liquidx.net/>'
__contributors__ = ['Santiago M. Mola <cooldwind@gmail.com',
					'William Hubbs <w.d.hubbs@gmail.com']
__revision__ = '$Id: $'
__license__ = """Copyright (c) 2006, Alastair Tse, All rights reserved.
This following source code is licensed under the GPL v2 License."""

CONFIG_FILE = '.bugz'

