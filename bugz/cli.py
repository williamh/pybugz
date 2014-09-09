import getpass
from http.cookiejar import CookieJar, LWPCookieJar
import locale
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import xmlrpc.client

try:
	import readline
except ImportError:
	readline = None

from bugz.bugzilla import BugzillaProxy
from bugz.errhandling import BugzError
from bugz.log import log_info

BUGZ_COMMENT_TEMPLATE = \
"""
BUGZ: ---------------------------------------------------
%s
BUGZ: Any line beginning with 'BUGZ:' will be ignored.
BUGZ: ---------------------------------------------------
"""

DEFAULT_COOKIE_FILE = '.bugz_cookie'
DEFAULT_TOKEN_FILE = '.bugz_token'
DEFAULT_NUM_COLS = 80

#
# Auxiliary functions
#

def get_content_type(filename):
	return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

def raw_input_block():
	""" Allows multiple line input until a Ctrl+D is detected.

	@rtype: string
	"""
	target = ''
	while True:
		try:
			line = input()
			target += line + '\n'
		except EOFError:
			return target

#
# This function was lifted from Bazaar 1.9.
#
def terminal_width():
	"""Return estimated terminal width."""
	if sys.platform == 'win32':
		return win32utils.get_console_size()[0]
	width = DEFAULT_NUM_COLS
	try:
		import struct, fcntl, termios
		s = struct.pack('HHHH', 0, 0, 0, 0)
		x = fcntl.ioctl(1, termios.TIOCGWINSZ, s)
		width = struct.unpack('HHHH', x)[1]
	except IOError:
		pass
	if width <= 0:
		try:
			width = int(os.environ['COLUMNS'])
		except:
			pass
	if width <= 0:
		width = DEFAULT_NUM_COLS

	return width

def launch_editor(initial_text, comment_from = '',comment_prefix = 'BUGZ:'):
	"""Launch an editor with some default text.

	Lifted from Mercurial 0.9.
	@rtype: string
	"""
	(fd, name) = tempfile.mkstemp("bugz")
	f = os.fdopen(fd, "w")
	f.write(comment_from)
	f.write(initial_text)
	f.close()

	editor = (os.environ.get("BUGZ_EDITOR") or
			os.environ.get("EDITOR"))
	if editor:
		result = os.system("%s \"%s\"" % (editor, name))
		if result != 0:
			raise RuntimeError('Unable to launch editor: %s' % editor)

		new_text = open(name).read()
		new_text = re.sub('(?m)^%s.*\n' % comment_prefix, '', new_text)
		os.unlink(name)
		return new_text

	return ''

def block_edit(comment, comment_from = ''):
	editor = (os.environ.get('BUGZ_EDITOR') or
			os.environ.get('EDITOR'))

	if not editor:
		print(comment + ': (Press Ctrl+D to end)')
		new_text = raw_input_block()
		return new_text

	initial_text = '\n'.join(['BUGZ: %s'%line for line in comment.split('\n')])
	new_text = launch_editor(BUGZ_COMMENT_TEMPLATE % initial_text, comment_from)

	if new_text.strip():
		return new_text
	else:
		return ''

class PrettyBugz:
	def __init__(self, args):
		if hasattr(args, 'columns'):
			self.columns = args.columns
		else:
			self.columns = terminal_width()
		self.user = args.user
		self.password = args.password
		self.passwordcmd = args.passwordcmd
		self.skip_auth = args.skip_auth

		cookie_file = os.path.join(os.environ['HOME'], DEFAULT_COOKIE_FILE)
		self.cookiejar = LWPCookieJar(cookie_file)

		try:
			self.cookiejar.load()
		except IOError:
			pass

		self.token_file = os.path.join(os.environ['HOME'], DEFAULT_TOKEN_FILE)
		try:
			self.token = open(self.token_file).read().strip()
		except IOError:
			self.token = None

		if getattr(args, 'encoding'):
			log_info("The --encoding option is deprecated.");

		log_info("Using %s " % args.base)
		self.bz = BugzillaProxy(args.base, cookiejar=self.cookiejar)

	def get_input(self, prompt):
		return input(prompt)

	def set_token(self, *args):
		if args and self.token:
			args[0]['Bugzilla_token'] = self.token
		return args

	def call_bz(self, method, *args):
		"""Attempt to call method with args. Log in if authentication is required.
		"""
		try:
			return method(*self.set_token(*args))
		except xmlrpc.client.Fault as fault:
			# Fault code 410 means login required
			if fault.faultCode == 410 and not self.skip_auth:
				self.login()
				return method(*self.set_token(*args))
			raise

	def login(self, args=None):
		"""Authenticate a session.
		"""
		# prompt for username if we were not supplied with it
		if not self.user:
			log_info('No username given.')
			self.user = self.get_input('Username: ')

		# prompt for password if we were not supplied with it
		if not self.password:
			if not self.passwordcmd:
				log_info('No password given.')
				self.password = getpass.getpass()
			else:
				process = subprocess.Popen(self.passwordcmd, shell=True,
					stdout=subprocess.PIPE)
				self.password, _ = process.communicate()
				self.password = self.password.split('\n')[0]

		# perform login
		params = {}
		params['login'] = self.user
		params['password'] = self.password
		if args is not None:
			params['remember'] = True
		log_info('Logging in')
		try:
			self.bz.User.login(params)
		except xmlrpc.client.Fault as fault:
			raise BugzError("Can't login: " + fault.faultString)
		log_info('Logging in')
		result = self.bz.User.login(params)
		if 'token' in result:
			self.token = result['token']

		if args is not None:
			if self.token:
				fd = open(self.token_file, 'w')
				fd.write(self.token)
				fd.write('\n')
				fd.close()
				os.chmod(self.token_file, 0o600)
			else:
				self.cookiejar.save()
				os.chmod(self.cookiejar.filename, 0o600)

	def logout(self, args):
		log_info('logging out')
		try:
			self.bz.User.logout()
		except xmlrpc.client.Fault as fault:
			raise BugzError("Failed to logout: " + fault.faultString)

	def search(self, args):
		"""Performs a search on the bugzilla database with the keywords given on the title (or the body if specified).
		"""
		valid_keys = ['alias', 'assigned_to', 'component', 'creator',
			'limit', 'offset', 'op_sys', 'platform',
			'priority', 'product', 'resolution',
			'severity', 'status', 'version', 'whiteboard']

		search_opts = sorted([(opt, val) for opt, val in list(args.__dict__.items())
			if val is not None and opt in valid_keys])

		params = {}
		for key in args.__dict__:
			if key in valid_keys and getattr(args, key) is not None:
				params[key] = getattr(args, key)
		if getattr(args, 'terms'):
			params['summary'] = args.terms

		search_term = ' '.join(args.terms).strip()

		if not (params or search_term):
			raise BugzError('Please give search terms or options.')

		if search_term:
			log_msg = 'Searching for \'%s\' ' % search_term
		else:
			log_msg = 'Searching for bugs '

		if search_opts:
			log_info(log_msg + 'with the following options:')
			for opt, val in search_opts:
				log_info('   %-20s = %s' % (opt, val))
		else:
			log_info(log_msg)

		if 'status' not in params:
			params['status'] = ['CONFIRMED', 'IN_PROGRESS', 'UNCONFIRMED']
		else:
			for x in params['status'][:]:
				if x in ['all', 'ALL']:
					del params['status']

		result = self.call_bz(self.bz.Bug.search, params)['bugs']

		if not len(result):
			log_info('No bugs found.')
		else:
			self.list_bugs(result, args)

	def get(self, args):
		""" Fetch bug details given the bug id """
		log_info('Getting bug %s ..' % args.bugid)
		try:
			result = self.call_bz(self.bz.Bug.get, {'ids':[args.bugid]})
		except xmlrpc.client.Fault as fault:
			raise BugzError("Can't get bug #" + str(args.bugid) + ": " \
					+ fault.faultString)

		for bug in result['bugs']:
			self.show_bug_info(bug, args.attachments, args.comments)

	def post(self, args):
		"""Post a new bug"""

		# load description from file if possible
		if args.description_from is not None:
			try:
					if args.description_from == '-':
						args.description = sys.stdin.read()
					else:
						args.description = open( args.description_from, 'r').read()
			except IOError as e:
				raise BugzError('Unable to read from file: %s: %s' %
					(args.description_from, e))

		if not args.batch:
			log_info('Press Ctrl+C at any time to abort.')

			#
			#  Check all bug fields.
			#  XXX: We use "if not <field>" for mandatory fields
			#       and "if <field> is None" for optional ones.
			#

			# check for product
			if not args.product:
				while not args.product or len(args.product) < 1:
					args.product = self.get_input('Enter product: ')
			else:
				log_info('Enter product: %s' % args.product)

			# check for component
			if not args.component:
				while not args.component or len(args.component) < 1:
					args.component = self.get_input('Enter component: ')
			else:
				log_info('Enter component: %s' % args.component)

			# check for version
			# FIXME: This default behaviour is not too nice.
			if not args.version:
				line = self.get_input('Enter version (default: unspecified): ')
				if len(line):
					args.version = line
				else:
					args.version = 'unspecified'
			else:
				log_info('Enter version: %s' % args.version)

			# check for title
			if not args.summary:
				while not args.summary or len(args.summary) < 1:
					args.summary = self.get_input('Enter title: ')
			else:
				log_info('Enter title: %s' % args.summary)

			# check for description
			if not args.description:
				line = block_edit('Enter bug description: ')
				if len(line):
					args.description = line
			else:
				log_info('Enter bug description: %s' % args.description)

			# check for operating system
			if not args.op_sys:
				op_sys_msg = 'Enter operating system where this bug occurs: '
				line = self.get_input(op_sys_msg)
				if len(line):
					args.op_sys = line
			else:
				log_info('Enter operating system: %s' % args.op_sys)

			# check for platform
			if not args.platform:
				platform_msg = 'Enter hardware platform where this bug occurs: '
				line = self.get_input(platform_msg)
				if len(line):
					args.platform = line
			else:
				log_info('Enter hardware platform: %s' % args.platform)

			# check for default priority
			if args.priority is None:
				priority_msg ='Enter priority (eg. Normal) (optional): '
				line = self.get_input(priority_msg)
				if len(line):
					args.priority = line
			else:
				log_info('Enter priority (optional): %s' % args.priority)

			# check for default severity
			if args.severity is None:
				severity_msg ='Enter severity (eg. normal) (optional): '
				line = self.get_input(severity_msg)
				if len(line):
					args.severity = line
			else:
				log_info('Enter severity (optional): %s' % args.severity)

			# check for default alias
			if args.alias is None:
				alias_msg ='Enter an alias for this bug (optional): '
				line = self.get_input(alias_msg)
				if len(line):
					args.alias = line
			else:
				log_info('Enter alias (optional): %s' % args.alias)

			# check for default assignee
			if args.assigned_to is None:
				assign_msg ='Enter assignee (eg. liquidx@gentoo.org) (optional): '
				line = self.get_input(assign_msg)
				if len(line):
					args.assigned_to = line
			else:
				log_info('Enter assignee (optional): %s' % args.assigned_to)

			# check for CC list
			if args.cc is None:
				cc_msg = 'Enter a CC list (comma separated) (optional): '
				line = self.get_input(cc_msg)
				if len(line):
					args.cc = line.split(', ')
			else:
				log_info('Enter a CC list (optional): %s' % args.cc)

			# check for URL
			if args.url is None:
				url_msg = 'Enter a URL (optional): '
				line = self.get_input(url_msg)
				if len(line):
					args.url = line
			else:
				log_info('Enter a URL (optional): %s' % args.url)

			# fixme: groups

			# fixme: status

			# fixme: milestone

			if args.append_command is None:
				args.append_command = self.get_input('Append the output of the following command (leave blank for none): ')
			else:
				log_info('Append command (optional): %s' % args.append_command)

		# raise an exception if mandatory fields are not specified.
		if args.product is None:
			raise RuntimeError('Product not specified')
		if args.component is None:
			raise RuntimeError('Component not specified')
		if args.summary is None:
			raise RuntimeError('Title not specified')
		if args.description is None:
			raise RuntimeError('Description not specified')

		if not args.version:
			args.version = 'unspecified'

		# append the output from append_command to the description
		if args.append_command is not None and args.append_command != '':
			append_command_output = subprocess.getoutput(args.append_command)
			args.description = args.description + '\n\n' + '$ ' + args.append_command + '\n' +  append_command_output

		# print submission confirmation
		print('-' * (self.columns - 1))
		print('%-12s: %s' % ('Product', args.product))
		print('%-12s: %s' %('Component', args.component))
		print('%-12s: %s' % ('Title', args.summary))
		print('%-12s: %s' % ('Version', args.version))
		print('%-12s: %s' % ('Description', args.description))
		print('%-12s: %s' % ('Operating System', args.op_sys))
		print('%-12s: %s' % ('Platform', args.platform))
		print('%-12s: %s' % ('Priority', args.priority))
		print('%-12s: %s' % ('Severity', args.severity))
		print('%-12s: %s' % ('Alias', args.alias))
		print('%-12s: %s' % ('Assigned to', args.assigned_to))
		print('%-12s: %s' % ('CC', args.cc))
		print('%-12s: %s' % ('URL', args.url))
		# fixme: groups
		# fixme: status
		# fixme: Milestone
		print('-' * (self.columns - 1))

		if not args.batch:
			if args.default_confirm in ['Y','y']:
				confirm = input('Confirm bug submission (Y/n)? ')
			else:
				confirm = input('Confirm bug submission (y/N)? ')
			if len(confirm) < 1:
				confirm = args.default_confirm
			if confirm[0] not in ('y', 'Y'):
				log_info('Submission aborted')
				return

		params={}
		params['product'] = args.product
		params['component'] = args.component
		params['version'] = args.version
		params['summary'] = args.summary
		if args.description is not None:
			params['description'] = args.description
		if args.op_sys is not None:
			params['op_sys'] = args.op_sys
		if args.platform is not None:
			params['platform'] = args.platform
		if args.priority is not None:
			params['priority'] = args.priority
		if args.severity is not None:
			params['severity'] = args.severity
		if args.alias is not None:
			params['alias'] = args.alias
		if args.assigned_to is not None:
			params['assigned_to'] = args.assigned_to
		if args.cc is not None:
			params['cc'] = args.cc
		if args.url is not None:
			params['url'] = args.url

		result = self.call_bz(self.bz.Bug.create, params)
		log_info('Bug %d submitted' % result['id'])

	def modify(self, args):
		"""Modify an existing bug (eg. adding a comment or changing resolution.)"""
		if args.comment_from:
			try:
				if args.comment_from == '-':
					args.comment = sys.stdin.read()
				else:
					args.comment = open(args.comment_from, 'r').read()
			except IOError as e:
				raise BugzError('unable to read file: %s: %s' % \
					(args.comment_from, e))

		if args.comment_editor:
			args.comment = block_edit('Enter comment:')

		params = {}
		if args.blocks_add is not None or args.blocks_remove is not None:
			params['blocks'] = {}
		if args.depends_on_add is not None \
			or args.depends_on_remove is not None:
			params['depends_on'] = {}
		if args.cc_add is not None or args.cc_remove is not None:
			params['cc'] = {}
		if args.comment is not None:
			params['comment'] = {}
		if args.groups_add is not None or args.groups_remove is not None:
			params['groups'] = {}
		if args.keywords_set is not None:
			params['keywords'] = {}
		if args.see_also_add is not None or args.see_also_remove is not None:
			params['see_also'] = {}

		params['ids'] = [args.bugid]
		if args.alias is not None:
			params['alias'] = args.alias
		if args.assigned_to is not None:
			params['assigned_to'] = args.assigned_to
		if args.blocks_add is not None:
			params['blocks']['add'] = args.blocks_add
		if args.blocks_remove is not None:
			params['blocks']['remove'] = args.blocks_remove
		if args.depends_on_add is not None:
			params['depends_on']['add'] = args.depends_on_add
		if args.depends_on_remove is not None:
			params['depends_on']['remove'] = args.depends_on_remove
		if args.cc_add is not None:
			params['cc']['add'] = args.cc_add
		if args.cc_remove is not None:
			params['cc']['remove'] = args.cc_remove
		if args.comment is not None:
			params['comment']['body'] = args.comment
		if args.component is not None:
			params['component'] = args.component
		if args.dupe_of:
			params['dupe_of'] = args.dupe_of
			args.status = None
			args.resolution = None
		if args.groups_add is not None:
			params['groups']['add'] = args.groups_add
		if args.groups_remove is not None:
			params['groups']['remove'] = args.groups_remove
		if args.keywords_set is not None:
			params['keywords']['set'] = args.keywords_set
		if args.op_sys is not None:
			params['op_sys'] = args.op_sys
		if args.platform is not None:
			params['platform'] = args.platform
		if args.priority is not None:
			params['priority'] = args.priority
		if args.product is not None:
			params['product'] = args.product
		if args.resolution is not None:
			params['resolution'] = args.resolution
		if args.see_also_add is not None:
			params['see_also']['add'] = args.see_also_add
		if args.see_also_remove is not None:
			params['see_also']['remove'] = args.see_also_remove
		if args.severity is not None:
			params['severity'] = args.severity
		if args.status is not None:
			params['status'] = args.status
		if args.summary is not None:
			params['summary'] = args.summary
		if args.url is not None:
			params['url'] = args.url
		if args.version is not None:
			params['version'] = args.version
		if args.whiteboard is not None:
			params['whiteboard'] = args.whiteboard

		if args.fixed:
			params['status'] = 'RESOLVED'
			params['resolution'] = 'FIXED'

		if args.invalid:
			params['status'] = 'RESOLVED'
			params['resolution'] = 'INVALID'

		if len(params) < 2:
			raise BugzError('No changes were specified')
		result = self.call_bz(self.bz.Bug.update, params)
		for bug in result['bugs']:
			changes = bug['changes']
			if not len(changes):
				log_info('Added comment to bug %s' % bug['id'])
			else:
				log_info('Modified the following fields in bug %s' % bug['id'])
				for key in changes:
					log_info('%-12s: removed %s' %(key, changes[key]['removed']))
					log_info('%-12s: added %s' %(key, changes[key]['added']))

	def attachment(self, args):
		""" Download or view an attachment given the id."""
		log_info('Getting attachment %s' % args.attachid)

		params = {}
		params['attachment_ids'] = [args.attachid]
		result = self.call_bz(self.bz.Bug.attachments, params)
		result = result['attachments'][args.attachid]

		action = {True:'Viewing', False:'Saving'}
		log_info('%s attachment: "%s"' %
			(action[args.view], result['file_name']))
		safe_filename = os.path.basename(re.sub(r'\.\.', '',
												result['file_name']))

		if args.view:
			print(result['data'].data)
		else:
			if os.path.exists(result['file_name']):
				raise RuntimeError('Filename already exists')

			fd = open(safe_filename, 'wb')
			fd.write(result['data'].data)
			fd.close()

	def attach(self, args):
		""" Attach a file to a bug given a filename. """
		filename = args.filename
		content_type = args.content_type
		bugid = args.bugid
		summary = args.summary
		is_patch = args.is_patch
		comment = args.comment

		if not os.path.exists(filename):
			raise BugzError('File not found: %s' % filename)

		if content_type is None:
			content_type = get_content_type(filename)

		if comment is None:
			comment = block_edit('Enter optional long description of attachment')

		if summary is None:
			summary = os.path.basename(filename)

		params = {}
		params['ids'] = [bugid]

		fd = open(filename, 'rb')
		params['data'] = xmlrpc.client.Binary(fd.read())
		fd.close()

		params['file_name'] = os.path.basename(filename)
		params['summary'] = summary
		if not is_patch:
			params['content_type'] = content_type;
		params['comment'] = comment
		params['is_patch'] = is_patch
		result =  self.call_bz(self.bz.Bug.add_attachment, params)
		log_info("'%s' has been attached to bug %s" % (filename, bugid))

	def list_bugs(self, buglist, args):
		for bug in buglist:
			bugid = bug['id']
			status = bug['status']
			priority = bug['priority']
			severity = bug['severity']
			assignee = bug['assigned_to'].split('@')[0]
			desc = bug['summary']
			line = '%s' % (bugid)
			if args.show_status:
				line = '%s %-12s' % (line, status)
			if args.show_priority:
				line = '%s %-12s' % (line, priority)
			if args.show_severity:
				line = '%s %-12s' % (line, severity)
			line = '%s %-20s' % (line, assignee)
			line = '%s %s' % (line, desc)
			print(line[:self.columns])

		log_info("%i bug(s) found." % len(buglist))

	def show_bug_info(self, bug, show_attachments, show_comments):
		FieldMap = {
			'alias': 'Alias',
			'summary': 'Title',
			'status': 'Status',
			'resolution': 'Resolution',
			'product': 'Product',
			'component': 'Component',
			'version': 'Version',
			'platform': 'Hardware',
			'op_sys': 'OpSystem',
			'priority': 'Priority',
			'severity': 'Severity',
			'target_milestone': 'TargetMilestone',
			'assigned_to': 'AssignedTo',
			'url': 'URL',
			'whiteboard': 'Whiteboard',
			'keywords': 'Keywords',
			'depends_on': 'dependsOn',
			'blocks': 'Blocks',
			'creation_time': 'Reported',
			'creator': 'Reporter',
			'last_change_time': 'Updated',
			'cc': 'CC',
			'see_also': 'See Also',
		}
		SkipFields = ['is_open', 'id', 'is_confirmed',
				'is_creator_accessible', 'is_cc_accessible',
				'update_token']

		for field in bug:
			if field in SkipFields:
				continue
			if field in FieldMap:
				desc = FieldMap[field]
			else:
				desc = field
			value = bug[field]
			if field in ['cc', 'see_also']:
				for x in value:
					print('%-12s: %s' %  (desc, x))
			elif isinstance(value, list):
				s = ', '.join(["%s" % x for x in value])
				if s:
					print('%-12s: %s' % (desc, s))
			elif value is not None and value != '':
				print('%-12s: %s' % (desc, value))

		if show_attachments:
			bug_attachments = self.call_bz(self.bz.Bug.attachments, {'ids':[bug['id']]})
			bug_attachments = bug_attachments['bugs']['%s' % bug['id']]
			print('%-12s: %d' % ('Attachments', len(bug_attachments)))
			print()
			for attachment in bug_attachments:
				aid = attachment['id']
				desc = attachment['summary']
				when = attachment['creation_time']
				print('[Attachment] [%s] [%s]' % (aid, desc))

		if show_comments:
			bug_comments = self.call_bz(self.bz.Bug.comments, {'ids':[bug['id']]})
			bug_comments = bug_comments['bugs']['%s' % bug['id']]['comments']
			print()
			print('%-12s: %d' % ('Comments', len(bug_comments)))
			print()
			i = 0
			wrapper = textwrap.TextWrapper(width = self.columns,
				break_long_words = False,
				break_on_hyphens = False)
			for comment in bug_comments:
				who = comment['creator']
				when = comment['time']
				what = comment['text']
				print('[Comment #%d] %s : %s' % (i, who, when))
				print('-' * (self.columns - 1))

				if what is None:
					what = ''

				# print wrapped version
				for line in what.split('\n'):
					if len(line) < self.columns:
						print(line)
					else:
						for shortline in wrapper.wrap(line):
							print(shortline)
				print()
				i += 1
