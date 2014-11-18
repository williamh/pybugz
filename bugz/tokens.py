import configparser
import os


class Tokens:
	def __init__(self):
		self.token_file = os.path.expanduser('~/.bugz_tokens')
		self.tokens = configparser.ConfigParser()
		self.tokens.read(self.token_file)

	def get_token(self, connection):
		if connection in self.tokens.sections():
			return self.tokens[connection]['token']
		else:
			return None

	def set_token(self, connection, bz_token):
		if bz_token is not None:
			if connection not in self.tokens.sections():
				self.tokens.add_section(connection)
			self.tokens.set(connection, 'token', bz_token)

	def remove_token(self, connection):
		self.tokens.remove_section(connection)

	def save_tokens(self):
		try:
			with open(self.token_file, 'w') as fd:
				self.tokens.write(fd, True)
		except IOError:
			pass
		os.chmod(self.token_file, 0o600)
