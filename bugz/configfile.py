import ConfigParser
import os, glob
import sys

from bugz.errhandling import BugzError
from bugz.log import *

class Connection:
	name = "default"
	base = None
	columns = 0
	user = None
	password = None
	passwordcmd = None
	quiet = None
	skip_auth = None
	encoding = None
	cookie_file = "~/.bugz_cookie"
	status = None # set of statuses to be queried
	inherit = None

def handle_settings_connection(settings, newDef):
	oldDef = str(settings['default_connection'])
	if oldDef != newDef:
		log_debug("redefining default connection from '{0}' to '{1}'". \
				format(oldDef, newDef), 2)
		settings['default_connection'] = newDef

def handle_settings(settings, context, stack, cp, sec_name):
	log_debug("contains SETTINGS section named [{0}]".format(sec_name), 3)

	if cp.has_option(sec_name, 'homeconf'):
		settings['homeconf'] = cp.get(sec_name, 'homeconf')

	if cp.has_option(sec_name, 'connection'):
		handle_settings_connection(settings, cp.get(sec_name, 'connection'))

	# handle 'confdir' ~> explore and push target files into the stack
	if cp.has_option(sec_name, 'confdir'):
		confdir = cp.get(sec_name, 'confdir')
		full_confdir = os.path.expanduser(confdir)
		wildcard = os.path.join(full_confdir, '*.conf')
		log_debug("adding wildcard " + wildcard, 3)
		for cnffile in glob.glob(wildcard):
			log_debug(" ++ " + cnffile, 3)
			if cnffile in context['included']:
				log_debug("skipping (already included)")
				break
			stack.append(cnffile)

def handle_connection(settings, context, stack, parser, name):
	log_debug("reading connection '{0}'".format(name), 2)
	connection = None

	if name in settings['connections']:
		log_debug("redefining connection '{0}'".format(name), 2)
		connection = settings['connections'][name]
	else:
		connection = Connection()
		connection.name = name

	def fill(conn, id):
		if parser.has_option(name, id):
			val = parser.get(name, id)
			setattr(conn, id, val)
			if id == 'password':
				val = "*** hidden ***"
			log_debug("has {0} - {1}".format(id, val), 3)

	fill(connection, "base")
	fill(connection, "user")
	fill(connection, "password")
	fill(connection, "passwordcmd")
	fill(connection, "encoding")
	fill(connection, "columns")
	fill(connection, "inherit")

	if parser.has_option(name, "quiet"):
		connection.quiet = parser.getboolean(name, "quiet")

	if parser.has_option(name, 'query_statuses'):
		line = parser.get(name, 'query_statuses')
		lines = line.split()
		connection.status = lines

	settings['connections'][name] = connection

def parse_file(settings, context, stack):
	file_name = stack.pop()
	full_name = os.path.expanduser(file_name)

	context['included'][full_name] = None

	log_debug("parsing '" + file_name + "'", 1)

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

	for sec in cp.sections():
		if sec == "settings":
			handle_settings(settings, context, stack, cp, sec)
		else:
			handle_connection(settings, context, stack, cp, sec)

def discover_configs(file, homeConf=None):
	settings = {
		# where to look for user's configuration
		'homeconf' : '~/.bugzrc',
		# list of objects of Connection
		'connections' : {},
		'default_connection' : None,
	}
	context = {
		'included' : {},
	}
	stack = [ file ]

	# parse sys configs
	while len(stack) > 0:
		parse_file(settings, context, stack)

	if not homeConf:
		# the command-line option must win
		homeConf = settings['homeconf']

	if not os.path.isfile(os.path.expanduser(homeConf)):
		return settings

	# parse home configs
	stack = [ homeConf ]
	while len(stack) > 0:
		parse_file(settings, context, stack)

	# calculate inherit hierarchy
	defConn = None
	if "default" in settings['connections']:
		defConn = settings['connections']['default']
	for name,conn in settings['connections'].items():
		if name == "default":
			# the [default] section does not inherit from anybody
			conn.inherit = None
			continue

		if not conn.inherit:
			conn.inherit = defConn

		elif isinstance(conn.inherit, str):
			parent = conn.inherit
			if parent in settings['connections']:
				conn.inherit = settings['connections'][parent]
			else:
				raise BugzError("Bad inherit option in section {0}".format(name))

		else:
			raise BugzError("Bad inherit option in section {0}".format(name))

	return settings
