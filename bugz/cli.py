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
	pass


from bugz.exceptions import BugzError
from bugz.log import log_debug, log_info
from bugz.utils import block_edit, get_content_type


def list_bugs(buglist, conn):
	for bug in buglist:
		bugid = bug['id']
		status = bug['status']
		priority = bug['priority']
		severity = bug['severity']
		assignee = bug['assigned_to'].split('@')[0]
		creator = bug['creator']
		desc = bug['summary']
		line = '%s' % (bugid)
		if hasattr(conn, 'show_status'):
			line = '%s %-12s' % (line, status)
		if hasattr(conn, 'show_priority'):
			line = '%s %-12s' % (line, priority)
		if hasattr(conn, 'show_severity'):
			line = '%s %-12s' % (line, severity)
		line = '%s %-20s' % (line, assignee)
		line = '%s %-20s' % (line, creator)
		line = '%s %s' % (line, desc)
		print(line[:conn.columns])

	log_info("%i bug(s) found." % len(buglist))


def prompt_for_bug(conn):
	""" Prompt for the information for a bug
	"""
	log_info('Press Ctrl+C at any time to abort.')

	if not hasattr(conn, 'product'):
		product = None
		while not product or len(product) < 1:
			product = input('Enter product: ')
		conn.product = product
	else:
		log_info('Enter product: %s' % conn.product)

	if not hasattr(conn, 'component'):
		component = None
		while not component or len(component) < 1:
			component = input('Enter component: ')
		conn.component = component
	else:
		log_info('Enter component: %s' % conn.component)

	if not hasattr(conn, 'version'):
		line = input('Enter version (default: unspecified): ')
		if len(line):
			conn.version = line
		else:
			conn.version = 'unspecified'
	else:
		log_info('Enter version: %s' % conn.version)

	if not hasattr(conn, 'summary'):
		summary = None
		while not summary or len(summary) < 1:
			summary = input('Enter title: ')
		conn.summary = summary
	else:
		log_info('Enter title: %s' % conn.summary)

	if not hasattr(conn, 'description'):
		line = block_edit('Enter bug description: ')
		if len(line):
			conn.description = line
	else:
		log_info('Enter bug description: %s' % conn.description)

	if not hasattr(conn, 'op_sys'):
		op_sys_msg = 'Enter operating system where this bug occurs: '
		line = input(op_sys_msg)
		if len(line):
			conn.op_sys = line
	else:
		log_info('Enter operating system: %s' % conn.op_sys)

	if not hasattr(conn, 'platform'):
		platform_msg = 'Enter hardware platform where this bug occurs: '
		line = input(platform_msg)
		if len(line):
			conn.platform = line
	else:
		log_info('Enter hardware platform: %s' % conn.platform)

	if not hasattr(conn, 'priority'):
		priority_msg = 'Enter priority (eg. Normal) (optional): '
		line = input(priority_msg)
		if len(line):
			conn.priority = line
	else:
		log_info('Enter priority (optional): %s' % conn.priority)

	if not hasattr(conn, 'severity'):
		severity_msg = 'Enter severity (eg. normal) (optional): '
		line = input(severity_msg)
		if len(line):
			conn.severity = line
	else:
		log_info('Enter severity (optional): %s' % conn.severity)

	if not hasattr(conn, 'alias'):
		alias_msg = 'Enter an alias for this bug (optional): '
		line = input(alias_msg)
		if len(line):
			conn.alias = line
	else:
		log_info('Enter alias (optional): %s' % conn.alias)

	if not hasattr(conn, 'assigned_to'):
		assign_msg = 'Enter assignee (eg. liquidx@gentoo.org) (optional): '
		line = input(assign_msg)
		if len(line):
			conn.assigned_to = line
	else:
		log_info('Enter assignee (optional): %s' % conn.assigned_to)

	if not hasattr(conn, 'cc'):
		cc_msg = 'Enter a CC list (comma separated) (optional): '
		line = input(cc_msg)
		if len(line):
			conn.cc = re.split(r',\s*', line)
	else:
		log_info('Enter a CC list (optional): %s' % conn.cc)

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


def show_bug_info(bug, conn):
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

	if not hasattr(conn, 'no_attachments'):
		params = {'ids': [bug['id']]}
		bug_attachments = conn.call_bz(conn.bz.Bug.attachments, params)
		bug_attachments = bug_attachments['bugs']['%s' % bug['id']]
		print('%-12s: %d' % ('Attachments', len(bug_attachments)))
		print()
		for attachment in bug_attachments:
			aid = attachment['id']
			desc = attachment['summary']
			when = attachment['creation_time']
			print('[Attachment] [%s] [%s]' % (aid, desc))

	if not hasattr(conn, 'no_comments'):
		params = {'ids': [bug['id']]}
		bug_comments = conn.call_bz(conn.bz.Bug.comments, params)
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


def attach(conn):
	""" Attach a file to a bug given a filename. """
	filename = getattr(conn, 'filename', None)
	content_type = getattr(conn, 'content_type', None)
	bugid = getattr(conn, 'bugid', None)
	summary = getattr(conn, 'summary', None)
	is_patch = getattr(conn, 'is_patch', None)
	comment = getattr(conn, 'comment', None)

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
	params['content_type'] = content_type
	params['comment'] = comment
	if is_patch is not None:
		params['is_patch'] = is_patch
	login(conn)
	result = conn.call_bz(conn.bz.Bug.add_attachment, params)
	attachid = result['ids'][0]
	log_info('{0} ({1}) has been attached to bug {2}'.format(
		filename, attachid, bugid))


def attachment(conn):
	""" Download or view an attachment given the id."""
	log_info('Getting attachment %s' % conn.attachid)

	params = {}
	params['attachment_ids'] = [conn.attachid]

	if not conn.skip_auth:
		login(conn)

	result = conn.call_bz(conn.bz.Bug.attachments, params)
	result = result['attachments'][conn.attachid]
	view = hasattr(conn, 'view')

	action = {True: 'Viewing', False: 'Saving'}
	log_info('%s attachment: "%s"' %
		(action[view], result['file_name']))
	safe_filename = os.path.basename(re.sub(r'\.\.', '',
											result['file_name']))

	if view:
		print(result['data'].data.decode('utf-8'))
	else:
		if os.path.exists(result['file_name']):
			raise RuntimeError('Filename already exists')

		fd = open(safe_filename, 'wb')
		fd.write(result['data'].data)
		fd.close()


def get(conn):
	""" Fetch bug details given the bug id """
	if not conn.skip_auth:
		login(conn)

	log_info('Getting bug %s ..' % conn.bugid)
	params = {'ids': [conn.bugid]}
	result = conn.call_bz(conn.bz.Bug.get, params)

	for bug in result['bugs']:
		show_bug_info(bug, conn)


def login(conn):
	"""Authenticate a session.
	"""
	conn.load_token()
	if conn.bz_token is not None:
		return

	# prompt for username if we were not supplied with it
	if not hasattr(conn, 'user'):
		log_info('No username given.')
		user = input('Username: ')
	else:
		user = conn.user

	# prompt for password if we were not supplied with it
	if not hasattr(conn, 'password'):
		if not hasattr(conn, 'passwordcmd'):
			log_info('No password given.')
			password = getpass.getpass()
		else:
			process = subprocess.Popen(conn.passwordcmd, shell=True,
				stdout=subprocess.PIPE)
			password, _ = process.communicate()
			password = password.splitlines()[0]
	else:
		password = conn.password

	# perform login
	params = {}
	params['login'] = user
	params['password'] = password
	log_info('Logging in')
	result = conn.call_bz(conn.bz.User.login, params)
	if 'token' in result:
		conn.save_token(result['token'])


def logout(conn):
	conn.load_token()
	params = {}
	log_info('logging out')
	conn.call_bz(conn.bz.User.logout, params)
	conn.destroy_token()


def modify(conn):
	"""Modify an existing bug (eg. adding a comment or changing resolution.)"""
	if hasattr(conn, 'comment_from'):
		try:
			if conn.comment_from == '-':
				conn.comment = sys.stdin.read()
			else:
				conn.comment = open(conn.comment_from, 'r').read()
		except IOError as e:
			raise BugzError('unable to read file: %s: %s' %
				(conn.comment_from, e))

	if hasattr(conn, 'comment_editor'):
		conn.comment = block_edit('Enter comment:')

	params = {}
	params['ids'] = [conn.bugid]
	if hasattr(conn, 'alias'):
		params['alias'] = conn.alias
	if hasattr(conn, 'assigned_to'):
		params['assigned_to'] = conn.assigned_to
	if hasattr(conn, 'blocks_add'):
		if 'blocks' not in params:
			params['blocks'] = {}
		params['blocks']['add'] = conn.blocks_add
	if hasattr(conn, 'blocks_remove'):
		if 'blocks' not in params:
			params['blocks'] = {}
		params['blocks']['remove'] = conn.blocks_remove
	if hasattr(conn, 'depends_on_add'):
		if 'depends_on' not in params:
			params['depends_on'] = {}
		params['depends_on']['add'] = conn.depends_on_add
	if hasattr(conn, 'depends_on_remove'):
		if 'depends_on' not in params:
			params['depends_on'] = {}
		params['depends_on']['remove'] = conn.depends_on_remove
	if hasattr(conn, 'cc_add'):
		if 'cc' not in params:
			params['cc'] = {}
		params['cc']['add'] = conn.cc_add
	if hasattr(conn, 'cc_remove'):
		if 'cc' not in params:
			params['cc'] = {}
		params['cc']['remove'] = conn.cc_remove
	if hasattr(conn, 'comment'):
		if 'comment' not in params:
			params['comment'] = {}
		params['comment']['body'] = conn.comment
	if hasattr(conn, 'component'):
		params['component'] = conn.component
	if hasattr(conn, 'dupe_of'):
		params['dupe_of'] = conn.dupe_of
	if hasattr(conn, 'groups_add'):
		if 'groups' not in params:
			params['groups'] = {}
		params['groups']['add'] = conn.groups_add
	if hasattr(conn, 'groups_remove'):
		if 'groups' not in params:
			params['groups'] = {}
		params['groups']['remove'] = conn.groups_remove
	if hasattr(conn, 'keywords_set'):
		if 'keywords' not in params:
			params['keywords'] = {}
		params['keywords']['set'] = conn.keywords_set
	if hasattr(conn, 'op_sys'):
		params['op_sys'] = conn.op_sys
	if hasattr(conn, 'platform'):
		params['platform'] = conn.platform
	if hasattr(conn, 'priority'):
		params['priority'] = conn.priority
	if hasattr(conn, 'product'):
		params['product'] = conn.product
	if hasattr(conn, 'resolution'):
		if not hasattr(conn, 'dupe_of'):
			params['resolution'] = conn.resolution
	if hasattr(conn, 'see_also_add'):
		if 'see_also' not in params:
			params['see_also'] = {}
		params['see_also']['add'] = conn.see_also_add
	if hasattr(conn, 'see_also_remove'):
		if 'see_also' not in params:
			params['see_also'] = {}
		params['see_also']['remove'] = conn.see_also_remove
	if hasattr(conn, 'severity'):
		params['severity'] = conn.severity
	if hasattr(conn, 'status'):
		if not hasattr(conn, 'dupe_of'):
			params['status'] = conn.status
	if hasattr(conn, 'summary'):
		params['summary'] = conn.summary
	if hasattr(conn, 'url'):
		params['url'] = conn.url
	if hasattr(conn, 'version'):
		params['version'] = conn.version
	if hasattr(conn, 'whiteboard'):
		params['whiteboard'] = conn.whiteboard

	if hasattr(conn, 'fixed'):
		params['status'] = 'RESOLVED'
		params['resolution'] = 'FIXED'

	if hasattr(conn, 'invalid'):
		params['status'] = 'RESOLVED'
		params['resolution'] = 'INVALID'

	if len(params) < 2:
		raise BugzError('No changes were specified')
	login(conn)
	result = conn.call_bz(conn.bz.Bug.update, params)
	for bug in result['bugs']:
		changes = bug['changes']
		if not len(changes):
			log_info('Added comment to bug %s' % bug['id'])
		else:
			log_info('Modified the following fields in bug %s' % bug['id'])
			for key in changes:
				log_info('%-12s: removed %s' % (key, changes[key]['removed']))
				log_info('%-12s: added %s' % (key, changes[key]['added']))


def post(conn):
	"""Post a new bug"""
	login(conn)
	# load description from file if possible
	if hasattr(conn, 'description_from'):
		try:
				if conn.description_from == '-':
					conn.description = sys.stdin.read()
				else:
					conn.description = open(conn.description_from, 'r').read()
		except IOError as e:
			raise BugzError('Unable to read from file: %s: %s' %
				(conn.description_from, e))

	if not hasattr(conn, 'batch'):
		prompt_for_bug(conn)

	# raise an exception if mandatory fields are not specified.
	if not hasattr(conn, 'product'):
		raise RuntimeError('Product not specified')
	if not hasattr(conn, 'component'):
		raise RuntimeError('Component not specified')
	if not hasattr(conn, 'summary'):
		raise RuntimeError('Title not specified')
	if not hasattr(conn, 'description'):
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
	if hasattr(conn, 'version'):
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

	if not hasattr(conn, 'batch'):
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
	if hasattr(conn, 'version'):
		params['version'] = conn.version
	params['summary'] = conn.summary
	if hasattr(conn, 'description'):
		params['description'] = conn.description
	if hasattr(conn, 'op_sys'):
		params['op_sys'] = conn.op_sys
	if hasattr(conn, 'platform'):
		params['platform'] = conn.platform
	if hasattr(conn, 'priority'):
		params['priority'] = conn.priority
	if hasattr(conn, 'severity'):
		params['severity'] = conn.severity
	if hasattr(conn, 'alias'):
		params['alias'] = conn.alias
	if hasattr(conn, 'assigned_to'):
		params['assigned_to'] = conn.assigned_to
	if hasattr(conn, 'cc'):
		params['cc'] = conn.cc
	if hasattr(conn, 'url'):
		params['url'] = conn.url

	result = conn.call_bz(conn.bz.Bug.create, params)
	log_info('Bug %d submitted' % result['id'])


def search(conn):
	"""Performs a search on the bugzilla database with
the keywords given on the title (or the body if specified).
	"""
	valid_keys = ['alias', 'assigned_to', 'component', 'creator',
		'limit', 'offset', 'op_sys', 'platform',
		'priority', 'product', 'resolution', 'severity',
		'version', 'whiteboard']

	params = {}
	d = vars(conn)
	for key in d:
		if key in valid_keys:
			params[key] = d[key]
	if 'status' in d:
		if 'all' not in d['status']:
			params['status'] = d['status']
	elif 'search_statuses' in d:
				params['status'] = d['search_statuses']
	if 'terms' in d:
		params['summary'] = d['terms']
		search_term = ' '.join(d['terms']).strip()

	if not params:
		raise BugzError('Please give search terms or options.')

	log_info('Searching for bugs meeting the following criteria:')
	for key in params:
		log_info('   {0:<20} = {1}'.format(key, params[key]))

	if not conn.skip_auth:
		login(conn)

	result = conn.call_bz(conn.bz.Bug.search, params)['bugs']

	if not len(result):
		log_info('No bugs found.')
	else:
		list_bugs(result, conn)


def connections(conn):
	print('Known bug trackers:')
	print()
	for tracker in conn.connections:
		print(tracker)
