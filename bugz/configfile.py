import ConfigParser
import os, glob
import sys
import pdb

from bugz.errhandling import BugzError
from bugz.log import *

DEFAULT_CONFIG_FILE = '~/.bugzrc'

def config_option(parser, get, section, option):
	if parser.has_option(section, option):
		try:
			if get(section, option) != '':
				return get(section, option)
			else:
				print " ! Error: "+option+" is not set"
				sys.exit(1)
		except ValueError, e:
			print " ! Error: option "+option+" is not in the right format: "+str(e)
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

class Connection:
	name = "default"
	base = 'https://bugs.gentoo.org/xmlrpc.cgi'
	columns = 0
	user = None
	password = None

def handle_default(settings, context, stack, cp):
	log_debug("handling the [default] section")

	if cp.has_option('default', 'connection'):
		oldDef = str(settings['default'])
		newDef = cp.get('default', 'connection')
		if oldDef != newDef:
			log_debug("redefining default connection from '{0}' to '{1}'". \
					format(oldDef, newDef))
			settings['default'] = newDef

	cp.remove_section("default")

def handle_settings(settings, context, stack, cp):
	log_debug("contains [settings]")

	if cp.has_option('settings', 'homeconf'):
		settings['homeconf'] = cp.get('settings', 'homeconf')

	# handle 'confdir' ~> explore and push target files into the stack
	if cp.has_option('settings', 'confdir'):
		confdir = cp.get('settings', 'confdir')
		full_confdir = os.path.expanduser(confdir)
		wildcard = os.path.join(full_confdir, '*.conf')
		log_debug("adding wildcard " + wildcard)
		for cnffile in glob.glob(wildcard):
			log_debug(" ++ " + cnffile)
			if cnffile in context['included']:
				log_debug("skipping (already included)")
				break
			stack.append(cnffile)

	cp.remove_section('settings')

def handle_connection(settings, context, stack, parser, name):
	log_debug("reading connection '{0}'".format(name))
	connection = None

	if name in settings['connections']:
		log_warn("redefining connection '{0}'".format(name))
		connection = settings['connections'][name]
	else:
		connection = Connection()
		connection.name = name

	def fill(tgt, id):
		if parser.has_option(name, id):
			log_debug("has {0}".format(id), 3)
			tgt = parser.get(name, id)

	if parser.has_option(name, "base"):
		connection.url = parser.get(name, "base")

	if parser.has_option(name, "columns"):
		connection.columns = parser.getint(name, "columns")

	fill(connection.user, "user")
	fill(connection.password, "password")

	settings['connections'][name] = connection

def parse_file(settings, context, stack):
	file_name = stack.pop()
	full_name = os.path.expanduser(file_name)

	context['included'][full_name] = None

	log_debug("parsing '" + file_name + "'")

	cp = ConfigParser.ConfigParser()
	parsed = None
	try:
		parsed = cp.read(full_name)
		if parsed != [ full_name ]:
			raise BugzError("problem with file '" + file_name + "'")
	except ConfigParser.Error, err:
		msg = err.message
		raise BugzError("can't parse: '" + file_name + "'\n" + msg )

	# successfully parsed file

	if "settings" in cp.sections():
		handle_settings(settings, context, stack, cp)

	if "default" in cp.sections():
		handle_default(settings, context, stack, cp)

	for sec in cp.sections():
		sectype = "connection"

		if cp.has_option(sec, 'type'):
			sectype = cp.get(sec, 'type')

		if sectype == "connection":
			handle_connection(settings, context, stack, cp, sec)

def parse_configs(file):
	settings = {
		# where to look for user's configuration
		'homeconf' : '~/.bugzrc',
		# list of objects of Connection
		'connections' : {},
		# the default Connection name
		'default' : None,
	}
	context = {
		'where' : 'sys',
		'homeparsed' : False,
		'included' : {},
	}
	stack = [ file ]

	# parse sys configs
	while len(stack) > 0:
		parse_file(settings, context, stack)

	# parse home configs
	stack = [ settings['homeconf'] ]
	while len(stack) > 0:
		parse_file(settings, context, stack)

	return settings

def get_config(userRedefined):
	settings = parse_configs(DEFAULT_CONFIG_FILE)
	sys.exit(1)
	return

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
			print " ! Error: Can't find user configuration file: "+config_file_name
			sys.exit(1)
		else:
			return

	# try to parse config file
	try:
		parser.readfp(file)
		sections = parser.sections()
	except ConfigParser.ParsingError, e:
		print " ! Error: Can't parse user configuration file: "+str(e)
		sys.exit(1)

	# parse the default section first
	if "default" in sections:
		fill_config(args, parser, "default")
	if section is None:
		section = config_option(parser, parser.get, "default", "connection")

	# parse a specific section
	if section in sections:
		fill_config(args, parser, section)
	elif section is not None:
		print " ! Error: Can't find section ["+section+"] in configuration file"
		sys.exit(1)
