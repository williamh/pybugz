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

from bugzilla import Bugz
from config import config

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

class PrettyBugz(Bugz):
	def __init__(self, base, user = None, password =None, forget = False,
			columns = 0, encoding = '', skip_auth = False,
			quiet = False, httpuser = None, httppassword = None ):

		self.quiet = quiet
		self.columns = columns or terminal_width()

		Bugz.__init__(self, base, user, password, forget, skip_auth, httpuser, httppassword)

		self.log("Using %s " % self.base)

		if not encoding:
			try:
				self.enc = locale.getdefaultlocale()[1]
			except:
				self.enc = 'utf-8'

			if not self.enc:
				self.enc = 'utf-8'
		else:
			self.enc = encoding

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

	def search(self, **kwds):
		"""Performs a search on the bugzilla database with the keywords given on the title (or the body if specified).
		"""
		search_term = ' '.join(kwds['terms']).strip()
		del kwds['terms']
		show_status = kwds['show_status']
		del kwds['show_status']
		show_url = kwds['show_url']
		del kwds['show_url']
		search_opts = sorted([(opt, val) for opt, val in kwds.items()
			if val is not None and opt != 'order'])

		if not (search_term or search_opts):
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

		result = Bugz.search(self, search_term, **kwds)

		if result is None:
			raise RuntimeError('Failed to perform search')

		if len(result) == 0:
			self.log('No bugs found.')
			return

		self.listbugs(result, show_url, show_status)

	def namedcmd(self, command, show_status=False, show_url=False):
		"""Run a command stored in Bugzilla by name."""
		log_msg = 'Running namedcmd \'%s\''%command
		result = Bugz.namedcmd(self, command)
		if result is None:
			raise RuntimeError('Failed to run command\nWrong namedcmd perhaps?')

		if len(result) == 0:
			self.log('No result from command')
			return

		self.listbugs(result, show_url, show_status)

	def get(self, bugid, comments = True, attachments = True):
		""" Fetch bug details given the bug id """
		self.log('Getting bug %s ..' % bugid)

		result = Bugz.get(self, bugid)

		if result is None:
			raise RuntimeError('Bug %s not found' % bugid)

		# Print out all the fields below by extract the text
		# directly from the tag, and just ignore if we don't
		# see the tag.
		FIELDS = (
			('short_desc', 'Title'),
			('assigned_to', 'Assignee'),
			('creation_ts', 'Reported'),
			('delta_ts', 'Updated'),
			('bug_status', 'Status'),
			('resolution', 'Resolution'),
			('bug_file_loc', 'URL'),
			('bug_severity', 'Severity'),
			('priority', 'Priority'),
			('reporter', 'Reporter'),
		)

		MORE_FIELDS = (
			('product', 'Product'),
			('component', 'Component'),
			('status_whiteboard', 'Whiteboard'),
			('keywords', 'Keywords'),
		)

		for field, name in FIELDS + MORE_FIELDS:
			try:
				value = result.find('.//%s' % field).text
				if value is None:
						continue
			except AttributeError:
				continue
			print '%-12s: %s' % (name, value.encode(self.enc))

		# Print out the cc'ed people
		cced = result.findall('.//cc')
		for cc in cced:
			print '%-12s: %s' %  ('CC', cc.text)

		# print out depends
		dependson = ', '.join([d.text for d in result.findall('.//dependson')])
		blocked = ', '.join([d.text for d in result.findall('.//blocked')])
		if dependson:
			print '%-12s: %s' % ('DependsOn', dependson)
		if blocked:
			print '%-12s: %s' % ('Blocked', blocked)

		bug_comments = result.findall('.//long_desc')
		bug_attachments = result.findall('.//attachment')

		print '%-12s: %d' % ('Comments', len(bug_comments))
		print '%-12s: %d' % ('Attachments', len(bug_attachments))
		print

		if attachments:
			for attachment in bug_attachments:
				aid = attachment.find('.//attachid').text
				desc = attachment.find('.//desc').text
				when = attachment.find('.//date').text
				print '[Attachment] [%s] [%s]' % (aid, desc.encode(self.enc))

		if comments:
			i = 0
			wrapper = textwrap.TextWrapper(width = self.columns)
			for comment in bug_comments:
				try:
					who = comment.find('.//who').text.encode(self.enc)
				except AttributeError:
					# Novell doesn't use 'who' on xml
					who = ""
				when = comment.find('.//bug_when').text.encode(self.enc)
				what =  comment.find('.//thetext').text
				print '\n[Comment #%d] %s : %s'  % (i, who, when)
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

	def post(self, product = None, component = None,
			title = None, description = None, assigned_to = None,
			cc = None, url = None, keywords = None,
			description_from = None, prodversion = None, append_command = None,
			dependson = None, blocked = None, batch = False,
			default_confirm = 'y', priority = None, severity = None):
		"""Post a new bug"""

		# load description from file if possible
		if description_from:
			try:
					if description_from == '-':
						description = sys.stdin.read()
					else:
						description = open(description_from, 'r').read()
			except IOError, e:
				raise BugzError('Unable to read from file: %s: %s' % \
								(description_from, e))

		if not batch:
			self.log('Press Ctrl+C at any time to abort.')

			#
			#  Check all bug fields.
			#  XXX: We use "if not <field>" for mandatory fields
			#       and "if <field> is None" for optional ones.
			#

			# check for product
			if not product:
				while not product or len(product) < 1:
					product = self.get_input('Enter product: ')
			else:
				self.log('Enter product: %s' % product)

			# check for component
			if not component:
				while not component or len(component) < 1:
					component = self.get_input('Enter component: ')
			else:
				self.log('Enter component: %s' % component)

			# check for version
			# FIXME: This default behaviour is not too nice.
			if prodversion is None:
				prodversion = self.get_input('Enter version (default: unspecified): ')
			else:
				self.log('Enter version: %s' % prodversion)

			# check for default severity
			if severity is None:
				severity_msg ='Enter severity (eg. normal) (optional): '
				severity = self.get_input(severity_msg)
			else:
				self.log('Enter severity (optional): %s' % severity)

			# fixme: hw platform
			# fixme: os
			# fixme: milestone

			# check for default priority
			if priority is None:
				priority_msg ='Enter priority (eg. Normal) (optional): '
				priority = self.get_input(priority_msg)
			else:
				self.log('Enter priority (optional): %s' % priority)

			# fixme: status

			# check for default assignee
			if assigned_to is None:
				assigned_msg ='Enter assignee (eg. liquidx@gentoo.org) (optional): '
				assigned_to = self.get_input(assigned_msg)
			else:
				self.log('Enter assignee (optional): %s' % assigned_to)

			# check for CC list
			if cc is None:
				cc_msg = 'Enter a CC list (comma separated) (optional): '
				cc = self.get_input(cc_msg)
			else:
				self.log('Enter a CC list (optional): %s' % cc)

			# check for optional URL
			if url is None:
				url = self.get_input('Enter URL (optional): ')
			else:
				self.log('Enter URL (optional): %s' % url)

			# check for title
			if not title:
				while not title or len(title) < 1:
					title = self.get_input('Enter title: ')
			else:
				self.log('Enter title: %s' % title)

			# check for description
			if not description:
				description = block_edit('Enter bug description: ')
			else:
				self.log('Enter bug description: %s' % description)

			if append_command is None:
				append_command = self.get_input('Append the output of the following command (leave blank for none): ')
			else:
				self.log('Append command (optional): %s' % append_command)

			# check for Keywords list
			if keywords is None:
				kwd_msg = 'Enter a Keywords list (comma separated) (optional): '
				keywords = self.get_input(kwd_msg)
			else:
				self.log('Enter a Keywords list (optional): %s' % keywords)

			# check for bug dependencies
			if dependson is None:
				dependson_msg = 'Enter a list of bug dependencies (comma separated) (optional): '
				dependson = self.get_input(dependson_msg)
			else:
				self.log('Enter a list of bug dependencies (optional): %s' % dependson)

			# check for blocker bugs
			if blocked is None:
				blocked_msg = 'Enter a list of blocker bugs (comma separated) (optional): '
				blocked = self.get_input(blocked_msg)
			else:
				self.log('Enter a list of blocker bugs (optional): %s' % blocked)

		# fixme: groups
		# append the output from append_command to the description
		if append_command is not None and append_command != '':
			append_command_output = commands.getoutput(append_command)
			description = description + '\n\n' + '$ ' + append_command + '\n' +  append_command_output

		# raise an exception if mandatory fields are not specified.
		if product is None:
			raise RuntimeError('Product not specified')
		if component is None:
			raise RuntimeError('Component not specified')
		if title is None:
			raise RuntimeError('Title not specified')
		if description is None:
			raise RuntimeError('Description not specified')

		# set optional fields to their defaults if they are not set.
		if prodversion is None:
			prodversion = ''
		if priority is None:
			priority = ''
		if severity is None:
			severity = ''
		if assigned_to is None:
			assigned_to = ''
		if cc is None:
			cc = ''
		if url is None:
			url = ''
		if keywords is None:
			keywords = ''
		if dependson is None:
			dependson = ''
		if blocked is None:
			blocked = ''

		# print submission confirmation
		print '-' * (self.columns - 1)
		print 'Product     : ' + product
		print 'Component   : ' + component
		print 'Version     : ' + prodversion
		print 'severity    : ' + severity
		# fixme: hardware
		# fixme: OS
		# fixme: Milestone
		print 'priority    : ' + priority
		# fixme: status
		print 'Assigned to : ' + assigned_to
		print 'CC          : ' + cc
		print 'URL         : ' + url
		print 'Title       : ' + title
		print 'Description : ' + description
		print 'Keywords    : ' + keywords
		print 'Depends on  : ' + dependson
		print 'Blocks      : ' + blocked
		# fixme: groups
		print '-' * (self.columns - 1)

		if not batch:
			if default_confirm in ['Y','y']:
				confirm = raw_input('Confirm bug submission (Y/n)? ')
			else:
				confirm = raw_input('Confirm bug submission (y/N)? ')
			if len(confirm) < 1:
				confirm = default_confirm
			if confirm[0] not in ('y', 'Y'):
				self.log('Submission aborted')
				return

		result = Bugz.post(self, product, component, title, description, url, assigned_to, cc, keywords, prodversion, dependson, blocked, priority, severity)
		if result is not None and result != 0:
			self.log('Bug %d submitted' % result)
		else:
			raise RuntimeError('Failed to submit bug')

	def modify(self, bugid, **kwds):
		"""Modify an existing bug (eg. adding a comment or changing resolution.)"""
		if 'comment_from' in kwds:
			if kwds['comment_from']:
				try:
					if kwds['comment_from'] == '-':
						kwds['comment'] = sys.stdin.read()
					else:
						kwds['comment'] = open(kwds['comment_from'], 'r').read()
				except IOError, e:
					raise BugzError('Failed to get read from file: %s: %s' % \
									(kwds['comment_from'], e))

				if 'comment_editor' in kwds:
					if kwds['comment_editor']:
						kwds['comment'] = block_edit('Enter comment:', kwds['comment'])
						del kwds['comment_editor']

			del kwds['comment_from']

		if 'comment_editor' in kwds:
			if kwds['comment_editor']:
				kwds['comment'] = block_edit('Enter comment:')
			del kwds['comment_editor']

		if kwds['fixed']:
			kwds['status'] = 'RESOLVED'
			kwds['resolution'] = 'FIXED'
		del kwds['fixed']

		if kwds['invalid']:
			kwds['status'] = 'RESOLVED'
			kwds['resolution'] = 'INVALID'
		del kwds['invalid']
		result = Bugz.modify(self, bugid, **kwds)
		if not result:
			raise RuntimeError('Failed to modify bug')
		else:
			self.log('Modified bug %s with the following fields:' % bugid)
			for field, value in result:
				self.log('  %-12s: %s' % (field, value))

	def attachment(self, attachid, view = False):
		""" Download or view an attachment given the id."""
		self.log('Getting attachment %s' % attachid)

		result = Bugz.attachment(self, attachid)
		if not result:
			raise RuntimeError('Unable to get attachment')

		action = {True:'Viewing', False:'Saving'}
		self.log('%s attachment: "%s"' % (action[view], result['filename']))
		safe_filename = os.path.basename(re.sub(r'\.\.', '',
												result['filename']))

		if view:
			print result['fd'].read()
		else:
			if os.path.exists(result['filename']):
				raise RuntimeError('Filename already exists')

			open(safe_filename, 'wb').write(result['fd'].read())

	def attach(self, bugid, filename, content_type = 'text/plain', patch = False, description = None):
		""" Attach a file to a bug given a filename. """
		if not os.path.exists(filename):
			raise BugzError('File not found: %s' % filename)
		if not description:
			description = block_edit('Enter description (optional)')
		result = Bugz.attach(self, bugid, filename, description, filename,
				content_type, patch)
		if result == True:
			self.log("'%s' has been attached to bug %s" % (filename, bugid))
		else:
			reason = ""
			if result and result != False:
				reason = "\nreason: %s" % result
			raise RuntimeError("Failed to attach '%s' to bug %s%s" % (filename,
				bugid, reason))

	def listbugs(self, buglist, show_url=False, show_status=False):
		x = ''
		if re.search("/$", self.base) is None:
			x = '/'
		for row in buglist:
			bugid = row['bugid']
			if show_url:
				bugid = '%s%s%s?id=%s'%(self.base, x, config.urls['show'], bugid)
			status = row['status']
			desc = row['desc']
			line = '%s' % (bugid)
			if show_status:
				line = '%s %s' % (line, status)
			if row.has_key('assignee'): # Novell does not have 'assignee' field
				assignee = row['assignee'].split('@')[0]
				line = '%s %-20s' % (line, assignee)

			line = '%s %s' % (line, desc)

			try:
				print line.encode(self.enc)[:self.columns]
			except UnicodeDecodeError:
				print line[:self.columns]

		self.log("%i bug(s) found." % len(buglist))
