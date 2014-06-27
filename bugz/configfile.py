import ConfigParser
import os
import sys

from bugz.log import log_error

DEFAULT_CONFIG_FILE = '~/.bugzrc'

def config_option(parser, get, section, option):
	if parser.has_option(section, option):
		try:
			if get(section, option) != '':
				return get(section, option)
			else:
				log_error("Error: "+option+" is not set")
				sys.exit(1)
		except ValueError, e:
			log_error("Error: option "+option+
					" is not in the right format: "+str(e))
			sys.exit(1)

def fill_config_option(args, parser, get, section, option):
	value = config_option(parser, get, section, option)
	if value is not None:
		setattr(args, option, value)

def fill_config(args, parser, section):
	fill_config_option(args, parser, parser.get, section, 'base')
	fill_config_option(args, parser, parser.get, section, 'user')
	fill_config_option(args, parser, parser.get, section, 'password')
	fill_config_option(args, parser, parser.get, section, 'passwordcmd')
	fill_config_option(args, parser, parser.getint, section, 'columns')
	fill_config_option(args, parser, parser.get, section, 'encoding')
	fill_config_option(args, parser, parser.getboolean, section, 'quiet')

def get_config(exe_name, args):
	config_file = getattr(args, 'config_file')
	if config_file is None:
			config_file = DEFAULT_CONFIG_FILE
	section = getattr(args, 'connection')
	parser = ConfigParser.ConfigParser()
	config_file_name = os.path.expanduser(config_file)

	# try to open config file
	try:
		file = open(config_file_name)
	except IOError:
		if getattr(args, 'config_file') is not None:
			log_error("Error: Can't find user configuration file: "
					+config_file_name)
			sys.exit(1)
		else:
			return

	# try to parse config file
	try:
		parser.readfp(file)
		sections = parser.sections()
	except ConfigParser.ParsingError, e:
		log_error("Error: Can't parse user configuration file: "+str(e))
		sys.exit(1)

	# parse the default section first
	if "default" in sections:
		fill_config(args, parser, "default")
	if section is None:
		# 'bugz-alias' handling
		for i in sections:
			bugz_alias = config_option(parser, parser.get, i, "bugz-alias")
			if exe_name == bugz_alias:
				section = i
				break
		else:
			section = config_option(parser, parser.get, "default", "connection")

	# parse a specific section
	if section in sections:
		fill_config(args, parser, section)
	elif section is not None:
		log_error("Error: Can't find section ["+section
			+"] in configuration file")
		sys.exit(1)
