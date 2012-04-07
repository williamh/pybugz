#!/usr/bin/env python

import commands
import locale
import os
import re
import sys
import tempfile
import textwrap

from urlparse import urljoin

try:
	import readline
except ImportError:
	readline = None

from bugzilla import BugzillaProxy

BUGZ_COMMENT_TEMPLATE = \
"""
BUGZ: ---------------------------------------------------
%s
BUGZ: Any line beginning with 'BUGZ:' will be ignored.
BUGZ: ---------------------------------------------------
"""

DEFAULT_NUM_COLS = 80

#
# Auxiliary functions
#

def raw_input_block():
	""" Allows multiple line input until a Ctrl+D is detected.

	@rtype: string
	"""
	target = ''
	while True:
		try:
			line = raw_input()
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
		print comment + ': (Press Ctrl+D to end)'
		new_text = raw_input_block()
		return new_text

	initial_text = '\n'.join(['BUGZ: %s'%line for line in comment.split('\n')])
	new_text = launch_editor(BUGZ_COMMENT_TEMPLATE % initial_text, comment_from)

	if new_text.strip():
		return new_text
	else:
		return ''

#
# Bugz specific exceptions
#

class BugzError(Exception):
	pass

class PrettyBugz:
	def __init__(self, args):
		self.quiet = args.quiet
		self.columns = args.columns or terminal_width()
		self.base = args.base

		self.bz = BugzillaProxy(self.base)
		self.log("Using %s " % self.base)

		if not args.skip_auth and (getattr(args, 'username', None) and
				getattr(args, 'password', None)):
			self.log('Logging in')
			self.bz.User.login({'login':args.username,'password':args.password})

		if not getattr(args, 'encoding'):
			try:
				self.enc = locale.getdefaultlocale()[1]
			except:
				self.enc = 'utf-8'

			if not self.enc:
				self.enc = 'utf-8'
		else:
			self.enc = args.encoding

	def log(self, status_msg, newline = True):
		if not self.quiet:
			if newline:
				print ' * %s' % status_msg
			else:
				print ' * %s' % status_msg,

	def warn(self, warn_msg):
		if not self.quiet:
			print ' ! Warning: %s' % warn_msg

	def get_input(self, prompt):
		return raw_input(prompt)

	def search(self, args):
		"""Performs a search on the bugzilla database with the keywords given on the title (or the body if specified).
		"""
		search_dict = {}
		skip_opts = ['base', 'columns', 'connection', 'comments',
				'encoding', 'forget', 'func', 'order', 'quiet', 'show_status',
			'skip_auth', 'terms']

		search_opts = sorted([(opt, val) for opt, val in args.__dict__.items()
			if val is not None and not opt in skip_opts])

		for key in args.__dict__.keys():
			if not key in skip_opts and getattr(args, key) is not None:
				search_dict[key] = getattr(args, key)

		search_term = ' '.join(args.terms).strip()

		if not (search_dict or search_term):
			raise BugzError('Please give search terms or options.')

		if search_term:
			log_msg = 'Searching for \'%s\' ' % search_term
		else:
			log_msg = 'Searching for bugs '

		if search_opts:
			self.log(log_msg + 'with the following options:')
			for opt, val in search_opts:
				self.log('   %-20s = %s' % (opt, val))
		else:
			self.log(log_msg)

		if not 'status' in search_dict.keys():
			search_dict['status'] = ['CONFIRMED', 'IN_PROGRESS', 'UNCONFIRMED']
		elif 'ALL' in search_dict['status']:
			del search_dict['status']

		result = self.bz.Bug.search(search_dict)
		buglist = result['bugs']

		if not len(buglist):
			self.log('No bugs found.')
		else:
			self.listbugs(buglist, args.show_status)

	def namedcmd(self, args):
		"""Run a command stored in Bugzilla by name."""
		log_msg = 'Running namedcmd \'%s\''%args.command
		result = Bugz.namedcmd(self, args)
		if result is None:
			raise RuntimeError('Failed to run command\nWrong namedcmd perhaps?')

		if len(result) == 0:
			self.log('No result from command')
			return

		self.listbugs(result, args.show_status)

	def get(self, args):
		""" Fetch bug details given the bug id """
		self.log('Getting bug %s ..' % args.bugid)
		result = self.bz.Bug.get({'ids':[args.bugid]})

		for bug in result['bugs']:
			self.showbuginfo(bug, args.attachments, args.comments)

	def post(self, args):
		"""Post a new bug"""

		# load description from file if possible
		if args.description_from is not None:
			print args.description_from
			sys.exit(1)
			try:
					if args.description_from == '-':
						args.description = sys.stdin.read()
					else:
						args.description = open( args.description_from, 'r').read()
			except IOError, e:
				raise BugzError('Unable to read from file: %s: %s' %
					(args.description_from, e))

		if not args.batch:
			self.log('Press Ctrl+C at any time to abort.')

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
				self.log('Enter product: %s' % args.product)

			# check for component
			if not args.component:
				while not args.component or len(args.component) < 1:
					args.component = self.get_input('Enter component: ')
			else:
				self.log('Enter component: %s' % args.component)

			# check for version
			# FIXME: This default behaviour is not too nice.
			if args.prodversion is None:
				args.prodversion = self.get_input('Enter version (default: unspecified): ')
			else:
				self.log('Enter version: %s' % args.prodversion)

			# check for default severity
			if args.severity is None:
				severity_msg ='Enter severity (eg. normal) (optional): '
				args.severity = self.get_input(severity_msg)
			else:
				self.log('Enter severity (optional): %s' % severity)

			# fixme: hw platform
			# fixme: os
			# fixme: milestone

			# check for default priority
			if args.priority is None:
				priority_msg ='Enter priority (eg. Normal) (optional): '
				args.priority = self.get_input(priority_msg)
			else:
				self.log('Enter priority (optional): %s' % args.priority)

			# fixme: status

			# check for default assignee
			if args.assigned_to is None:
				assigned_msg ='Enter assignee (eg. liquidx@gentoo.org) (optional): '
				args.assigned_to = self.get_input(assigned_msg)
			else:
				self.log('Enter assignee (optional): %s' % args.assigned_to)

			# check for CC list
			if args.cc is None:
				cc_msg = 'Enter a CC list (comma separated) (optional): '
				args.cc = self.get_input(cc_msg)
			else:
				self.log('Enter a CC list (optional): %s' % args.cc)

			# check for optional URL
			if args.url is None:
				args.url = self.get_input('Enter URL (optional): ')
			else:
				self.log('Enter URL (optional): %s' % args.url)

			# check for title
			if not args.title:
				while not args.title or len(args.title) < 1:
					args.title = self.get_input('Enter title: ')
			else:
				self.log('Enter title: %s' % args.title)

			# check for description
			if not args.description:
				args.description = block_edit('Enter bug description: ')
			else:
				self.log('Enter bug description: %s' % args.description)

			if args.append_command is None:
				args.append_command = self.get_input('Append the output of the following command (leave blank for none): ')
			else:
				self.log('Append command (optional): %s' % args.append_command)

			# check for Keywords list
			if args.keywords is None:
				kwd_msg = 'Enter a Keywords list (comma separated) (optional): '
				args.keywords = self.get_input(kwd_msg)
			else:
				self.log('Enter a Keywords list (optional): %s' % args.keywords)

			# check for bug dependencies
			if args.dependson is None:
				dependson_msg = 'Enter a list of bug dependencies (comma separated) (optional): '
				args.dependson = self.get_input(dependson_msg)
			else:
				self.log('Enter a list of bug dependencies (optional): %s'
					% args.dependson)

			# check for blocker bugs
			if args.blocked is None:
				blocked_msg = 'Enter a list of blocker bugs (comma separated) (optional): '
				args.blocked = self.get_input(blocked_msg)
			else:
				self.log('Enter a list of blocker bugs (optional): %s' %
						args.blocked)

		# fixme: groups
		# append the output from append_command to the description
		if args.append_command is not None and args.append_command != '':
			append_command_output = commands.getoutput(args.append_command)
			args.description = args.description + '\n\n' + '$ ' + args.append_command + '\n' +  append_command_output

		# raise an exception if mandatory fields are not specified.
		if args.product is None:
			raise RuntimeError('Product not specified')
		if args.component is None:
			raise RuntimeError('Component not specified')
		if args.title is None:
			raise RuntimeError('Title not specified')
		if args.description is None:
			raise RuntimeError('Description not specified')

		# set optional fields to their defaults if they are not set.
		if args.prodversion is None:
			args.prodversion = ''
		if args.priority is None:
			args.priority = ''
		if args.severity is None:
			args.severity = ''
		if args.assigned_to is None:
			args.assigned_to = ''
		if args.cc is None:
			args.cc = ''
		if args.url is None:
			args.url = ''
		if args.keywords is None:
			args.keywords = ''
		if args.dependson is None:
			args.dependson = ''
		if args.blocked is None:
			args.blocked = ''

		# print submission confirmation
		print '-' * (self.columns - 1)
		print 'Product     : ' + args.product
		print 'Component   : ' + args.component
		print 'Version     : ' + args.prodversion
		print 'severity    : ' + args.severity
		# fixme: hardware
		# fixme: OS
		# fixme: Milestone
		print 'priority    : ' + args.priority
		# fixme: status
		print 'Assigned to : ' + args.assigned_to
		print 'CC          : ' + args.cc
		print 'URL         : ' + args.url
		print 'Title       : ' + args.title
		print 'Description : ' + args.description
		print 'Keywords    : ' + args.keywords
		print 'Depends on  : ' + args.dependson
		print 'Blocks      : ' + args.blocked
		# fixme: groups
		print '-' * (self.columns - 1)

		if not args.batch:
			if args.default_confirm in ['Y','y']:
				confirm = raw_input('Confirm bug submission (Y/n)? ')
			else:
				confirm = raw_input('Confirm bug submission (y/N)? ')
			if len(confirm) < 1:
				confirm = args.default_confirm
			if confirm[0] not in ('y', 'Y'):
				self.log('Submission aborted')
				return

		result = Bugz.post(self, args)
		if result is not None and result != 0:
			self.log('Bug %d submitted' % result)
		else:
			raise RuntimeError('Failed to submit bug')

	def modify(self, args):
		"""Modify an existing bug (eg. adding a comment or changing resolution.)"""
		if args.comment_from:
			try:
				if args.comment_from == '-':
					args.comment = sys.stdin.read()
				else:
					args.comment = open(args.comment_from, 'r').read()
			except IOError, e:
				raise BugzError('unable to read file: %s: %s' % \
					(args.comment_from, e))

		if args.comment_editor:
			args.comment = block_edit('Enter comment:')

		if args.fixed:
			args.status = 'RESOLVED'
			args.resolution = 'FIXED'

		if args.invalid:
			args.status = 'RESOLVED'
			args.resolution = 'INVALID'
		result = Bugz.modify(self, args)
		if not result:
			raise RuntimeError('Failed to modify bug')
		else:
			self.log('Modified bug %s with the following fields:' %
					args.bugid)
			for field, value in result:
				self.log('  %-12s: %s' % (field, value))

	def attachment(self, args):
		""" Download or view an attachment given the id."""
		self.log('Getting attachment %s' % args.attachid)

		result = Bugz.attachment(self, args)
		if not result:
			raise RuntimeError('Unable to get attachment')

		action = {True:'Viewing', False:'Saving'}
		self.log('%s attachment: "%s"' % (action[args.view], result['filename']))
		safe_filename = os.path.basename(re.sub(r'\.\.', '',
												result['filename']))

		if args.view:
			print result['fd'].read()
		else:
			if os.path.exists(result['filename']):
				raise RuntimeError('Filename already exists')

			open(safe_filename, 'wb').write(result['fd'].read())

	def attach(self, args):
		""" Attach a file to a bug given a filename. """
		if not os.path.exists(args.filename):
			raise BugzError('File not found: %s' % args.filename)
		if not args.description:
			args.description = block_edit('Enter description (optional)')
		result = Bugz.attach(self,args)
		if result == True:
			self.log("'%s' has been attached to bug %s" %
				(args.filename, args.bugid))
		else:
			reason = ""
			if result and result != False:
				reason = "\nreason: %s" % result
			raise RuntimeError("Failed to attach '%s' to bug %s%s" %
				(args.filename, args.bugid, reason))

	def listbugs(self, buglist, show_status=False):
		for bug in buglist:
			bugid = bug['id']
			status = bug['status']
			assignee = bug['assigned_to'].split('@')[0]
			desc = bug['summary']
			line = '%s' % (bugid)
			if show_status:
				line = '%s %s' % (line, status)
			line = '%s %-20s' % (line, assignee)
			line = '%s %s' % (line, desc)

			try:
				print line.encode(self.enc)[:self.columns]
			except UnicodeDecodeError:
				print line[:self.columns]

		self.log("%i bug(s) found." % len(buglist))

	def showbuginfo(self, bug, show_attachments, show_comments):
		FIELDS = (
			('summary', 'Title'),
			('assigned_to', 'Assignee'),
			('creation_time', 'Reported'),
			('last_change_time', 'Updated'),
			('status', 'Status'),
			('resolution', 'Resolution'),
			('url', 'URL'),
			('severity', 'Severity'),
			('priority', 'Priority'),
			('creator', 'Reporter'),
		)

		MORE_FIELDS = (
			('product', 'Product'),
			('component', 'Component'),
			('whiteboard', 'Whiteboard'),
		)

		for field, name in FIELDS + MORE_FIELDS:
			try:
				value = bug[field]
				if value is None or value == '':
						continue
			except AttributeError:
				continue
			print '%-12s: %s' % (name, value)

		# print keywords
		k = ', '.join(bug['keywords'])
		if k:
			print '%-12s: %s' % ('Keywords', k)

		# Print out the cc'ed people
		cced = bug['cc']
		for cc in cced:
			print '%-12s: %s' %  ('CC', cc)

		# print out depends
		dependson = ', '.join(["%s" % x for x in bug['depends_on']])
		if dependson:
			print '%-12s: %s' % ('DependsOn', dependson)
		blocked = ', '.join(["%s" % x for x in bug['blocks']])
		if blocked:
			print '%-12s: %s' % ('Blocked', blocked)

		bug_comments = self.bz.Bug.comments({'ids':[bug['id']]})
		bug_comments = bug_comments['bugs']['%s' % bug['id']]['comments']
		print '%-12s: %d' % ('Comments', len(bug_comments))

		bug_attachments = self.bz.Bug.attachments({'ids':[bug['id']]})
		bug_attachments = bug_attachments['bugs']['%s' % bug['id']]
		print '%-12s: %d' % ('Attachments', len(bug_attachments))
		print

		if show_attachments:
			for attachment in bug_attachments:
				aid = attachment['id']
				desc = attachment['summary']
				when = attachment['creation_time']
				print '[Attachment] [%s] [%s]' % (aid, desc.encode(self.enc))

		if show_comments:
			i = 0
			wrapper = textwrap.TextWrapper(width = self.columns)
			for comment in bug_comments:
				who = comment['creator']
				when = comment['time']
				what = comment['text']
				print '\n[Comment #%d] %s : %s' % (i, who, when)
				print '-' * (self.columns - 1)

				if what is None:
					what = ''

				# print wrapped version
				for line in what.split('\n'):
					if len(line) < self.columns:
						print line.encode(self.enc)
					else:
						for shortline in wrapper.wrap(line):
							print shortline.encode(self.enc)
				i += 1
			print
