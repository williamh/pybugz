import configparser
import glob
import os
import sys

from bugz.log import log_error


def read_config(parser, ConfigFiles):
	try:
		parser.read(ConfigFiles)
	except configparser.DuplicateOptionError as e:
		log_error(e)
		sys.exit(1)
	except configparser.DuplicateSectionError as e:
		log_error(e)
		sys.exit(1)
	except configparser.MissingSectionHeaderError as e:
		log_error(e)
		sys.exit(1)
	except configparser.ParsingError as e:
		log_error(e)
		sys.exit(1)


def get_config(parser, UserConfig=None):
	DefaultConfigs = sorted(glob.glob(sys.prefix + '/share/pybugz.d/*.conf'))
	SystemConfigs = sorted(glob.glob('/etc/pybugz.d/*.conf'))
	if UserConfig is not None:
		UserConfig = os.path.expanduser(UserConfig)
	else:
		UserConfig = os.path.expanduser('~/.bugzrc')
	read_config(parser, DefaultConfigs)
	read_config(parser, SystemConfigs)
	read_config(parser, UserConfig)


def get_config_option(get, section, option):
	try:
		value = get(section, option)
		if value == '':
			log_error('{0} is not set'.format(option))
			sys.exit(1)

		return value
	except ValueError as e:
		log_error('{0} is not in the right format: {1}'.format(option,
			str(e)))
		sys.exit(1)
