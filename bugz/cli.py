import getpass
import os
import re
import subprocess
import sys
import textwrap
import xmlrpc.client

try:
	import readline
except ImportError:
	readline = None


from bugz.bugzilla import BugzillaProxy
from bugz.errhandling import BugzError
from bugz.log import log_info
from bugz.utils import block_edit, get_content_type

DEFAULT_TOKEN_FILE = '.bugz_token'


class PrettyBugz:
	def __init__(self, conn):
		self.conn = conn
		self.token_file = os.path.join(os.environ['HOME'], DEFAULT_TOKEN_FILE)
		try:
			self.token = open(self.token_file).read().strip()
		except IOError:
			self.token = None

		self.bz = BugzillaProxy(conn.base)

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
			if fault.faultCode == 410 and not self.conn.skip_auth:
				self.login(self.conn)
				return method(*self.set_token(*args))
			raise

	def login(self, conn):
		"""Authenticate a session.
		"""
		# prompt for username if we were not supplied with it
		if getattr(conn, 'user', None) is None:
			log_info('No username given.')
			conn.user = input('Username: ')

		# prompt for password if we were not supplied with it
		if getattr(conn, 'password', None) is None:
			if getattr(conn, 'passwordcmd', None) is None:
				log_info('No password given.')
				conn.password = getpass.getpass()
			else:
				process = subprocess.Popen(conn.passwordcmd, shell=True,
					stdout=subprocess.PIPE)
				conn.password, _ = process.communicate()
				conn.password = conn.password.splitlines()[0]

		# perform login
		params = {}
		params['login'] = conn.user
		params['password'] = conn.password
		log_info('Logging in')
		try:
			self.bz.User.login(params)
		except xmlrpc.client.Fault as fault:
			raise BugzError("Can't login: " + fault.faultString)
		log_info('Logging in')
		result = self.bz.User.login(params)
		if 'token' in result:
			self.token = result['token']

		if conn is not None:
			if self.token:
				fd = open(self.token_file, 'w')
				fd.write(self.token)
				fd.write('\n')
				fd.close()
				os.chmod(self.token_file, 0o600)

	def logout(self, conn):
		log_info('logging out')
		try:
			self.bz.User.logout()
		except xmlrpc.client.Fault as fault:
			raise BugzError("Failed to logout: " + fault.faultString)

	def search(self, conn):
		"""Performs a search on the bugzilla database with
the keywords given on the title (or the body if specified).
		"""
		valid_keys = ['alias', 'assigned_to', 'component', 'creator',
			'limit', 'offset', 'op_sys', 'platform',
			'priority', 'product', 'resolution',
			'severity', 'status', 'version', 'whiteboard']

		search_opts = sorted([(opt, val) for opt, val in list(conn.__dict__.items())
			if val is not None and opt in valid_keys])

		params = {}
		for key in conn.__dict__:
			if key in valid_keys and getattr(conn, key) is not None:
				params[key] = getattr(conn, key)
		if getattr(conn, 'terms'):
			params['summary'] = conn.terms

		search_term = ' '.join(conn.terms).strip()

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
			self.list_bugs(result, conn)

	def get(self, conn):
		""" Fetch bug details given the bug id """
		log_info('Getting bug %s ..' % conn.bugid)
		try:
			params = {'ids': [conn.bugid]}
			result = self.call_bz(self.bz.Bug.get, params)
		except xmlrpc.client.Fault as fault:
			raise BugzError("Can't get bug #" + str(conn.bugid) + ": "
					+ fault.faultString)

		for bug in result['bugs']:
			self.show_bug_info(bug, conn)

	def post(self, conn):
		"""Post a new bug"""

		# load description from file if possible
		if getattr(conn, 'description_from', None) is not None:
			try:
					if conn.description_from == '-':
						conn.description = sys.stdin.read()
					else:
						conn.description = open(conn.description_from, 'r').read()
			except IOError as e:
				raise BugzError('Unable to read from file: %s: %s' %
					(conn.description_from, e))

		if not conn.batch:
			log_info('Press Ctrl+C at any time to abort.')

			#  Check all bug fields.
			#

			# check for product
			if not hasattr(conn, 'product'):
				product = None
				while not product or len(product) < 1:
					product = input('Enter product: ')
				conn.product = product
			else:
				log_info('Enter product: %s' % conn.product)

			# check for component
			if not hasattr(conn, 'component'):
				component = None
				while not component or len(component) < 1:
					component = input('Enter component: ')
				conn.component = component
			else:
				log_info('Enter component: %s' % conn.component)

			# check for version
			if not hasattr(conn, 'version'):
				line = input('Enter version (default: unspecified): ')
				if len(line):
					conn.version = line
				else:
					conn.version = 'unspecified'
			else:
				log_info('Enter version: %s' % conn.version)

			# check for title
			if not hasattr(conn, 'summary'):
				summary = None
				while not summary or len(summary) < 1:
					summary = input('Enter title: ')
				conn.summary = summary
			else:
				log_info('Enter title: %s' % conn.summary)

			# check for description
			if not hasattr(conn, 'description'):
				line = block_edit('Enter bug description: ')
				if len(line):
					conn.description = line
			else:
				log_info('Enter bug description: %s' % conn.description)

			# check for operating system
			if not hasattr(conn, 'op_sys'):
				op_sys_msg = 'Enter operating system where this bug occurs: '
				line = input(op_sys_msg)
				if len(line):
					conn.op_sys = line
			else:
				log_info('Enter operating system: %s' % conn.op_sys)

			# check for platform
			if not hasattr(conn, 'platform'):
				platform_msg = 'Enter hardware platform where this bug occurs: '
				line = input(platform_msg)
				if len(line):
					conn.platform = line
			else:
				log_info('Enter hardware platform: %s' % conn.platform)

			# check for default priority
			if not hasattr(conn, 'priority'):
				priority_msg = 'Enter priority (eg. Normal) (optional): '
				line = input(priority_msg)
				if len(line):
					conn.priority = line
			else:
				log_info('Enter priority (optional): %s' % conn.priority)

			# check for default severity
			if not hasattr(conn, 'severity'):
				severity_msg = 'Enter severity (eg. normal) (optional): '
				line = input(severity_msg)
				if len(line):
					conn.severity = line
			else:
				log_info('Enter severity (optional): %s' % conn.severity)

			# check for default alias
			if not hasattr(conn, 'alias'):
				alias_msg = 'Enter an alias for this bug (optional): '
				line = input(alias_msg)
				if len(line):
					conn.alias = line
			else:
				log_info('Enter alias (optional): %s' % conn.alias)

			# check for default assignee
			if not hasattr(conn, 'assigned_to'):
				assign_msg = 'Enter assignee (eg. liquidx@gentoo.org) (optional): '
				line = input(assign_msg)
				if len(line):
					conn.assigned_to = line
			else:
				log_info('Enter assignee (optional): %s' % conn.assigned_to)

			# check for CC list
			if not hasattr(conn, 'cc'):
				cc_msg = 'Enter a CC list (comma separated) (optional): '
				line = input(cc_msg)
				if len(line):
					conn.cc = line.split(', ')
			else:
				log_info('Enter a CC list (optional): %s' % conn.cc)

			# check for URL
			if not hasattr(conn, 'url'):
				url_msg = 'Enter a URL (optional): '
				line = input(url_msg)
				if len(line):
					conn.url = line
			else:
				log_info('Enter a URL (optional): %s' % conn.url)

			# fixme: groups

			# fixme: status

			# fixme: milestone

			if not hasattr(conn, 'append_command'):
				line = input('Append the output of the'
				' following command (leave blank for none): ')
				if len(line):
					conn.append_command = line
			else:
				log_info('Append command (optional): %s' % conn.append_command)

		# raise an exception if mandatory fields are not specified.
		if getattr(conn, 'product', None) is None:
			raise RuntimeError('Product not specified')
		if getattr(conn, 'component', None) is None:
			raise RuntimeError('Component not specified')
		if getattr(conn, 'summary', None) is None:
			raise RuntimeError('Title not specified')
		if getattr(conn, 'description', None) is None:
			raise RuntimeError('Description not specified')

		# append the output from append_command to the description
		append_command = getattr(conn, 'append_command', None)
		if append_command is not None and append_command != '':
			append_command_output = subprocess.getoutput(append_command)
			conn.description = conn.description + '\n\n' + \
				'$ ' + append_command + '\n' + \
				append_command_output

		# print submission confirmation
		print('-' * (conn.columns - 1))
		print('%-12s: %s' % ('Product', conn.product))
		print('%-12s: %s' % ('Component', conn.component))
		print('%-12s: %s' % ('Title', conn.summary))
		print('%-12s: %s' % ('Version', conn.version))
		print('%-12s: %s' % ('Description', conn.description))
		if hasattr(conn, 'op_sys'):
			print('%-12s: %s' % ('Operating System', conn.op_sys))
		if hasattr(conn, 'platform'):
			print('%-12s: %s' % ('Platform', conn.platform))
		if hasattr(conn, 'priority'):
			print('%-12s: %s' % ('Priority', conn.priority))
		if hasattr(conn, 'severity'):
			print('%-12s: %s' % ('Severity', conn.severity))
		if hasattr(conn, 'alias'):
			print('%-12s: %s' % ('Alias', conn.alias))
		if hasattr(conn, 'assigned_to'):
			print('%-12s: %s' % ('Assigned to', conn.assigned_to))
		if hasattr(conn, 'cc'):
			print('%-12s: %s' % ('CC', conn.cc))
		if hasattr(conn, 'url'):
			print('%-12s: %s' % ('URL', conn.url))
		# fixme: groups
		# fixme: status
		# fixme: Milestone
		print('-' * (conn.columns - 1))

		if not getattr(conn, 'batch', None):
			if conn.default_confirm in ['Y', 'y']:
				confirm = input('Confirm bug submission (Y/n)? ')
			else:
				confirm = input('Confirm bug submission (y/N)? ')
			if len(confirm) < 1:
				confirm = conn.default_confirm
			if confirm[0] not in ('y', 'Y'):
				log_info('Submission aborted')
				return

		params = {}
		params['product'] = conn.product
		params['component'] = conn.component
		params['version'] = conn.version
		params['summary'] = conn.summary
		if getattr(conn, 'description', None) is not None:
			params['description'] = conn.description
		if getattr(conn, 'op_sys', None) is not None:
			params['op_sys'] = conn.op_sys
		if getattr(conn, 'platform', None) is not None:
			params['platform'] = conn.platform
		if getattr(conn, 'priority', None) is not None:
			params['priority'] = conn.priority
		if getattr(conn, 'severity', None) is not None:
			params['severity'] = conn.severity
		if getattr(conn, 'alias', None) is not None:
			params['alias'] = conn.alias
		if getattr(conn, 'assigned_to', None) is not None:
			params['assigned_to'] = conn.assigned_to
		if getattr(conn, 'cc', None) is not None:
			params['cc'] = conn.cc
		if getattr(conn, 'url', None) is not None:
			params['url'] = conn.url

		result = self.call_bz(self.bz.Bug.create, params)
		log_info('Bug %d submitted' % result['id'])

	def modify(self, conn):
		"""Modify an existing bug (eg. adding a comment or changing resolution.)"""
		if getattr(conn, 'comment_from', None) is not None:
			try:
				if conn.comment_from == '-':
					conn.comment = sys.stdin.read()
				else:
					conn.comment = open(conn.comment_from, 'r').read()
			except IOError as e:
				raise BugzError('unable to read file: %s: %s' %
					(conn.comment_from, e))

		if conn.comment_editor:
			conn.comment = block_edit('Enter comment:')

		params = {}
		params['ids'] = [conn.bugid]
		if getattr(conn, 'alias', None) is not None:
			params['alias'] = conn.alias
		if getattr(conn, 'assigned_to', None) is not None:
			params['assigned_to'] = conn.assigned_to
		if getattr(conn, 'blocks_add', None) is not None:
			if not 'blocks' in params:
				params['blocks'] = {}
			params['blocks']['add'] = conn.blocks_add
		if getattr(conn, 'blocks_remove', None) is not None:
			if not 'blocks' in params:
				params['blocks'] = {}
			params['blocks']['remove'] = conn.blocks_remove
		if getattr(conn, 'depends_on_add', None) is not None:
			if not 'depends_on' in params:
				params['depends_on'] = {}
			params['depends_on']['add'] = conn.depends_on_add
		if getattr(conn, 'depends_on_remove', None) is not None:
			if not 'depends_on' in params:
				params['depends_on'] = {}
			params['depends_on']['remove'] = conn.depends_on_remove
		if getattr(conn, 'cc_add', None) is not None:
			if not 'cc' in params:
				params['cc'] = {}
			params['cc']['add'] = conn.cc_add
		if getattr(conn, 'cc_remove', None) is not None:
			if not 'cc' in params:
				params['cc'] = {}
			params['cc']['remove'] = conn.cc_remove
		if getattr(conn, 'comment', None) is not None:
			if not 'comment' in params:
				params['comment'] = {}
			params['comment']['body'] = conn.comment
		if getattr(conn, 'component', None) is not None:
			params['component'] = conn.component
		if getattr(conn, 'dupe_of', None) is not None:
			params['dupe_of'] = conn.dupe_of
			del conn['status']
			del conn['resolution']
		if getattr(conn, 'groups_add', None) is not None:
			if not 'groups' in params:
				params['groups'] = {}
			params['groups']['add'] = conn.groups_add
		if getattr(conn, 'groups_remove', None) is not None:
			if not 'groups' in params:
				params['groups'] = {}
			params['groups']['remove'] = conn.groups_remove
		if getattr(conn, 'keywords_set', None) is not None:
			if not 'keywords' in params:
				params['keywords'] = {}
			params['keywords']['set'] = conn.keywords_set
		if getattr(conn, 'op_sys', None) is not None:
			params['op_sys'] = conn.op_sys
		if getattr(conn, 'platform', None) is not None:
			params['platform'] = conn.platform
		if getattr(conn, 'priority', None) is not None:
			params['priority'] = conn.priority
		if getattr(conn, 'product', None) is not None:
			params['product'] = conn.product
		if getattr(conn, 'resolution', None) is not None:
			params['resolution'] = conn.resolution
		if getattr(conn, 'see_also_add', None) is not None:
			if not 'see_also' in params:
				params['see_also'] = {}
			params['see_also']['add'] = conn.see_also_add
		if getattr(conn, 'see_also_remove', None) is not None:
			if not 'see_also' in params:
				params['see_also'] = {}
			params['see_also']['remove'] = conn.see_also_remove
		if getattr(conn, 'severity', None) is not None:
			params['severity'] = conn.severity
		if getattr(conn, 'status', None) is not None:
			params['status'] = conn.status
		if getattr(conn, 'summary', None) is not None:
			params['summary'] = conn.summary
		if getattr(conn, 'url', None) is not None:
			params['url'] = conn.url
		if getattr(conn, 'version', None) is not None:
			params['version'] = conn.version
		if getattr(conn, 'whiteboard', None) is not None:
			params['whiteboard'] = conn.whiteboard

		if getattr(conn, 'fixed', None):
			params['status'] = 'RESOLVED'
			params['resolution'] = 'FIXED'

		if getattr(conn, 'invalid', None):
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
					log_info('%-12s: removed %s' % (key, changes[key]['removed']))
					log_info('%-12s: added %s' % (key, changes[key]['added']))

	def attachment(self, conn):
		""" Download or view an attachment given the id."""
		log_info('Getting attachment %s' % conn.attachid)

		params = {}
		params['attachment_ids'] = [conn.attachid]
		result = self.call_bz(self.bz.Bug.attachments, params)
		result = result['attachments'][conn.attachid]
		view = getattr(conn, 'view', False)

		action = {True: 'Viewing', False: 'Saving'}
		log_info('%s attachment: "%s"' %
			(action[view], result['file_name']))
		safe_filename = os.path.basename(re.sub(r'\.\.', '',
												result['file_name']))

		if view:
			print(result['data'].data)
		else:
			if os.path.exists(result['file_name']):
				raise RuntimeError('Filename already exists')

			fd = open(safe_filename, 'wb')
			fd.write(result['data'].data)
			fd.close()

	def attach(self, conn):
		""" Attach a file to a bug given a filename. """
		filename = conn.filename
		content_type = conn.content_type
		bugid = conn.bugid
		summary = conn.summary
		is_patch = conn.is_patch
		comment = conn.comment

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
			params['content_type'] = content_type
		params['comment'] = comment
		params['is_patch'] = is_patch
		result = self.call_bz(self.bz.Bug.add_attachment, params)
		attachid = result['ids'][0]
		log_info('{0} ({1}) has been attached to bug {2}'.format(
			filename, attachid, bugid))

	def list_bugs(self, buglist, conn):
		for bug in buglist:
			bugid = bug['id']
			status = bug['status']
			priority = bug['priority']
			severity = bug['severity']
			assignee = bug['assigned_to'].split('@')[0]
			desc = bug['summary']
			line = '%s' % (bugid)
			if conn.show_status:
				line = '%s %-12s' % (line, status)
			if conn.show_priority:
				line = '%s %-12s' % (line, priority)
			if conn.show_severity:
				line = '%s %-12s' % (line, severity)
			line = '%s %-20s' % (line, assignee)
			line = '%s %s' % (line, desc)
			print(line[:conn.columns])

		log_info("%i bug(s) found." % len(buglist))

	def show_bug_info(self, bug, conn):
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
					print('%-12s: %s' % (desc, x))
			elif isinstance(value, list):
				s = ', '.join(["%s" % x for x in value])
				if s:
					print('%-12s: %s' % (desc, s))
			elif value is not None and value != '':
				print('%-12s: %s' % (desc, value))

		if not getattr(conn, 'no_attachments', False):
			params = {'ids': [bug['id']]}
			bug_attachments = self.call_bz(self.bz.Bug.attachments,
					params)
			bug_attachments = bug_attachments['bugs']['%s' % bug['id']]
			print('%-12s: %d' % ('Attachments', len(bug_attachments)))
			print()
			for attachment in bug_attachments:
				aid = attachment['id']
				desc = attachment['summary']
				when = attachment['creation_time']
				print('[Attachment] [%s] [%s]' % (aid, desc))

		if not getattr(conn, 'no_comments', False):
			params = {'ids': [bug['id']]}
			bug_comments = self.call_bz(self.bz.Bug.comments, params)
			bug_comments = bug_comments['bugs']['%s' % bug['id']]['comments']
			print('%-12s: %d' % ('Comments', len(bug_comments)))
			print()
			i = 0
			wrapper = textwrap.TextWrapper(width=conn.columns,
				break_long_words=False,
				break_on_hyphens=False)
			for comment in bug_comments:
				who = comment['creator']
				when = comment['time']
				what = comment['text']
				print('[Comment #%d] %s : %s' % (i, who, when))
				print('-' * (conn.columns - 1))

				if what is None:
					what = ''

				# print wrapped version
				for line in what.splitlines():
					if len(line) < conn.columns:
						print(line)
					else:
						for shortline in wrapper.wrap(line):
							print(shortline)
				print()
				i += 1
