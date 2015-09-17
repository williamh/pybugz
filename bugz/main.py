#!/usr/bin/env python3

"""
Python Bugzilla Interface

Simple command-line interface to bugzilla to allow:
 - searching
 - getting bug info
 - saving attachments

Requirements
------------
 - Python 3.3 or later

Classes
-------
 - BugzillaProxy - Server proxy for communication with Bugzilla

"""

import sys

from bugz.argparser import make_arg_parser
from bugz.configfile import load_config
from bugz.connection import Connection
from bugz.exceptions import BugzError
from bugz.log import log_error, log_info


def main():
	ArgParser = make_arg_parser()
	args = ArgParser.parse_args()

	ConfigParser = load_config(getattr(args, 'config_file', None))

	conn = Connection(args, ConfigParser)

	if not hasattr(args, 'func'):
		ArgParser.print_usage()
		return 1

	try:
		args.func(conn)
	except BugzError as e:
		log_error(e)
		return 1
	except RuntimeError as e:
		log_error(e)
		return 1
	except KeyboardInterrupt:
		log_info('Stopped due to keyboard interrupt')
		return 1

	return 0


if __name__ == "__main__":
	sys.exit(main())
