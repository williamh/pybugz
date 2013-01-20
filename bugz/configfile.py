import ConfigParser
import os, glob
import sys
import pdb

from bugz.errhandling import BugzError
from bugz.log import *

class Connection:
	name = "default"
	base = 'https://bugs.gentoo.org/xmlrpc.cgi'
	columns = 0
	user = None
	password = None
	password_cmd = None
	dbglvl = 0
	quiet = None
	skip_auth = None
	encoding = "utf-8"
	cookie_file = "~/.bugz_cookie"
	option_change = False
	query_statuses = []

	def dump(self):
		log_info("Using [{0}] ({1})".format(self.name, self.base))
		log_debug("User: '{0}'".format(self.user), 3)
		# loglvl == 4, only for developers (&& only by hardcoding)
		log_debug("Pass: '{0}'".format(self.password), 10)
		log_debug("Columns: {0}".format(self.columns), 3)

def handle_default(settings, newDef):
	oldDef = str(settings['default'])
	if oldDef != newDef:
		log_debug("redefining default connection from '{0}' to '{1}'". \
				format(oldDef, newDef), 2)
		settings['default'] = newDef

def handle_settings(settings, context, stack, cp, sec_name):
	log_debug("contains SETTINGS section named [{0}]".format(sec_name), 3)

	if cp.has_option(sec_name, 'homeconf'):
		settings['homeconf'] = cp.get(sec_name, 'homeconf')

	if cp.has_option(sec_name, 'default'):
		handle_default(settings, cp.get(sec_name, 'default'))

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
			log_debug("has {0} - {1}".format(id, val), 3)

	fill(connection, "base")
	fill(connection, "user")
	fill(connection, "password")
	fill(connection, "encoding")
	fill(connection, "columns")
	fill(connection, "quiet")

	if parser.has_option(name, 'query_statuses'):
		line = parser.get(name, 'query_statuses')
		lines = line.split()
		connection.query_statuses = lines

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
		sectype = "connection"

		if cp.has_option(sec, 'type'):
			sectype = cp.get(sec, 'type')

		if sectype == "settings":
			handle_settings(settings, context, stack, cp, sec)

		if sectype == "connection":
			handle_connection(settings, context, stack, cp, sec)

def discover_configs(file, homeConf=None):
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

	if not homeConf:
		# the command-line option must win
		homeConf = settings['homeconf']

	if not os.path.isfile(os.path.expanduser(homeConf)):
		return settings

	# parse home configs
	stack = [ homeConf ]
	while len(stack) > 0:
		parse_file(settings, context, stack)

	return settings
