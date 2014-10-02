import sys

from bugz.cli import PrettyBugz
from bugz.configfile import get_config_option
from bugz.log import log_debug, log_error, log_info
from bugz.log import log_setDebugLevel, log_setQuiet
from bugz.utils import terminal_width


class Connection:
	def __init__(self, args, config):
		for attr, value in args.__dict__.items():
			sv = getattr(self, attr, None)
			if sv != value:
				setattr(self, attr, value)

# Only remember login details when the login command is used.
		self.remember = getattr(self, 'func', None) == PrettyBugz.login

		if not hasattr(self, 'connection'):
			if config.has_option('default', 'connection'):
				self.connection = get_config_option(config.get,
					'default', 'connection')
			else:
				log_error('No default connection specified')
				sys.exit(1)

		if not self.connection in config.sections():
			log_error('connection "{0}" not found'.format(self.connection))
			sys.exit(1)

		if not hasattr(self, 'base'):
			if config.has_option(self.connection, 'base'):
				self.base = get_config_option(config.get,
					self.connection, 'base')
			else:
				log_error('No base URL specified')
				sys.exit(1)

		if not hasattr(self, 'user'):
			if config.has_option(self.connection, 'user'):
				self.user = get_config_option(config.get,
					self.connection, 'user')

		if not hasattr(self, 'password'):
			if config.has_option(self.connection, 'password'):
				self.password = get_config_option(config.get,
					self.connection, 'password')

		if not hasattr(self, 'passwordcmd'):
			if config.has_option(self.connection, 'passwordcmd'):
				self.passwordcmd = get_config_option(config.get,
					self.connection, 'passwordcmd')

		if not hasattr(self, 'skip_auth'):
			if config.has_option(self.connection, 'skip_auth'):
				self.skip_auth = get_config_option(config.get,
					self.connection, 'skip_auth')
			else:
				self.skip_auth = False

		if not hasattr(self, 'columns'):
			if config.has_option(self.connection, 'columns'):
				self.columns = get_config_option(config.getint,
					self.connection, 'columns')
			else:
				self.columns = terminal_width()

		if not hasattr(self, 'debug'):
			if config.has_option(self.connection, 'debug'):
				self.debug = get_config_option(config.getint,
					self.connection, 'debug')
			else:
				self.debug = 0

		if not hasattr(self, 'quiet'):
			if config.has_option(self.connection, 'quiet'):
				self.quiet = get_config_option(config.getboolean,
					self.connection, 'quiet')
			else:
				self.quiet = False

		if getattr(self, 'encoding', None) is not None:
			log_info('The encoding option is deprecated.')

		log_setDebugLevel(self.debug)
		log_setQuiet(self.quiet)

		log_info("Using [{0}] ({1})".format(self.connection, self.base))

		log_debug('Connection debug dump:', 3)
		for attr, value in self.__dict__.items():
			log_debug('{0}, {1}'.format(attr, getattr(self, attr)), 3)
