#!/usr/bin/env python

import base64
import csv
import getpass
import locale
import mimetypes
import os
import re
import sys

from cookielib import LWPCookieJar, CookieJar
from cStringIO import StringIO
from urlparse import urlsplit, urljoin
from urllib import urlencode, quote
from urllib2 import build_opener, HTTPCookieProcessor, Request

from config import config

from xml.etree import ElementTree

COOKIE_FILE = '.bugz_cookie'

#
# Return a string truncated to the given length if it is longer.
#

def ellipsis(text, length):
	if len(text) > length:
		return text[:length-4] + "..."
	else:
		return text

#
# HTTP file uploads in Python
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/146306
#

def post_multipart(host, selector, fields, files):
	"""
	Post fields and files to an http host as multipart/form-data.
	fields is a sequence of (name, value) elements for regular form fields.
	files is a sequence of (name, filename, value) elements for data to be uploaded as files
	Return the server's response page.
	"""
	content_type, body = encode_multipart_formdata(fields, files)
	h = httplib.HTTP(host)
	h.putrequest('POST', selector)
	h.putheader('content-type', content_type)
	h.putheader('content-length', str(len(body)))
	h.endheaders()
	h.send(body)
	errcode, errmsg, headers = h.getreply()
	return h.file.read()

def encode_multipart_formdata(fields, files):
	"""
	fields is a sequence of (name, value) elements for regular form fields.
	files is a sequence of (name, filename, value) elements for data to be uploaded as files
	Return (content_type, body) ready for httplib.HTTP instance
	"""
	BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
	CRLF = '\r\n'
	L = []
	for (key, value) in fields:
		L.append('--' + BOUNDARY)
		L.append('Content-Disposition: form-data; name="%s"' % key)
		L.append('')
		L.append(value)
	for (key, filename, value) in files:
		L.append('--' + BOUNDARY)
		L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
		L.append('Content-Type: %s' % get_content_type(filename))
		L.append('')
		L.append(value)
	L.append('--' + BOUNDARY + '--')
	L.append('')
	body = CRLF.join(L)
	content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
	return content_type, body

def get_content_type(filename):
	return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

#
# Override the behaviour of elementtree and allow us to
# force the encoding to utf-8
# Not needed in Python 2.7, since ElementTree.XMLTreeBuilder uses the forced
# encoding.
#

class ForcedEncodingXMLTreeBuilder(ElementTree.XMLTreeBuilder):
	def __init__(self, html = 0, target = None, encoding = None):
		try:
			from xml.parsers import expat
		except ImportError:
			raise ImportError(
				"No module named expat; use SimpleXMLTreeBuilder instead"
				)
		self._parser = parser = expat.ParserCreate(encoding, "}")
		if target is None:
			target = ElementTree.TreeBuilder()
		self._target = target
		self._names = {} # name memo cache
		# callbacks
		parser.DefaultHandlerExpand = self._default
		parser.StartElementHandler = self._start
		parser.EndElementHandler = self._end
		parser.CharacterDataHandler = self._data
		# let expat do the buffering, if supported
		try:
			self._parser.buffer_text = 1
		except AttributeError:
			pass
		# use new-style attribute handling, if supported
		try:
			self._parser.ordered_attributes = 1
			self._parser.specified_attributes = 1
			parser.StartElementHandler = self._start_list
		except AttributeError:
			pass
		encoding = None
		if not parser.returns_unicode:
			encoding = "utf-8"
		# target.xml(encoding, None)
		self._doctype = None
		self.entity = {}

#
# Real bugzilla interface
#

class Bugz:
	""" Converts sane method calls to Bugzilla HTTP requests.

	@ivar base: base url of bugzilla.
	@ivar user: username for authenticated operations.
	@ivar password: password for authenticated operations
	@ivar cookiejar: for authenticated sessions so we only auth once.
	@ivar forget: forget user/password after session.
	@ivar authenticated: is this session authenticated already
	"""

	def __init__(self, base, user = None, password = None, forget = False,
			skip_auth = False, httpuser = None, httppassword = None ):
		"""
		{user} and {password} will be prompted if an action needs them
		and they are not supplied.

		if {forget} is set, the login cookie will be destroyed on quit.

		@param base: base url of the bugzilla
		@type  base: string
		@keyword user: username for authenticated actions.
		@type    user: string
		@keyword password: password for authenticated actions.
		@type    password: string
		@keyword forget: forget login session after termination.
		@type    forget: bool
		@keyword skip_auth: do not authenticate
		@type    skip_auth: bool
		"""
		self.base = base
		scheme, self.host, self.path, query, frag  = urlsplit(self.base)
		self.authenticated = False
		self.forget = forget

		if not self.forget:
			try:
				cookie_file = os.path.join(os.environ['HOME'], COOKIE_FILE)
				self.cookiejar = LWPCookieJar(cookie_file)
				if forget:
					try:
						self.cookiejar.load()
						self.cookiejar.clear()
						self.cookiejar.save()
						os.chmod(self.cookiejar.filename, 0700)
					except IOError:
						pass
			except KeyError:
				self.warn('Unable to save session cookies in %s' % cookie_file)
				self.cookiejar = CookieJar(cookie_file)
		else:
			self.cookiejar = CookieJar()

		self.opener = build_opener(HTTPCookieProcessor(self.cookiejar))
		self.user = user
		self.password = password
		self.httpuser = httpuser
		self.httppassword = httppassword
		self.skip_auth = skip_auth

	def log(self, status_msg):
		"""Default logging handler. Expected to be overridden by
		the UI implementing subclass.

		@param status_msg: status message to print
		@type  status_msg: string
		"""
		return

	def warn(self, warn_msg):
		"""Default logging handler. Expected to be overridden by
		the UI implementing subclass.

		@param status_msg: status message to print
		@type  status_msg: string
		"""
		return

	def get_input(self, prompt):
		"""Default input handler. Expected to be override by the
		UI implementing subclass.

		@param prompt: Prompt message
		@type  prompt: string
		"""
		return ''

	def auth(self):
		"""Authenticate a session.
		"""
		# check if we need to authenticate
		if self.authenticated:
			return

		# try seeing if we really need to request login
		if not self.forget:
			try:
				self.cookiejar.load()
			except IOError:
				pass

		req_url = urljoin(self.base, config.urls['auth'])
		req_url += '?GoAheadAndLogIn=1'
		req = Request(req_url, None, config.headers)
		if self.httpuser and self.httppassword:
			base64string = base64.encodestring('%s:%s' % (self.httpuser, self.httppassword))[:-1]
			req.add_header("Authorization", "Basic %s" % base64string)
		resp = self.opener.open(req)
		re_request_login = re.compile(r'<title>.*Log in to .*</title>')
		if not re_request_login.search(resp.read()):
			self.log('Already logged in.')
			self.authenticated = True
			return

		# prompt for username if we were not supplied with it
		if not self.user:
			self.log('No username given.')
			self.user = self.get_input('Username: ')

		# prompt for password if we were not supplied with it
		if not self.password:
			self.log('No password given.')
			self.password = getpass.getpass()

		# perform login
		qparams = config.params['auth'].copy()
		qparams['Bugzilla_login'] = self.user
		qparams['Bugzilla_password'] = self.password
		if not self.forget:
			qparams['Bugzilla_remember'] = 'on'

		req_url = urljoin(self.base, config.urls['auth'])
		req = Request(req_url, urlencode(qparams), config.headers)
		if self.httpuser and self.httppassword:
			base64string = base64.encodestring('%s:%s' % (self.httpuser, self.httppassword))[:-1]
			req.add_header("Authorization", "Basic %s" % base64string)
		resp = self.opener.open(req)
		if resp.info().has_key('Set-Cookie'):
			self.authenticated = True
			if not self.forget:
				self.cookiejar.save()
				os.chmod(self.cookiejar.filename, 0700)
			return True
		else:
			raise RuntimeError("Failed to login")

	def extractResults(self, resp):
		# parse the results into dicts.
		results = []
		columns = []
		rows = []

		for r in csv.reader(resp): rows.append(r)
		for field in rows[0]:
			if config.choices['column_alias'].has_key(field):
				columns.append(config.choices['column_alias'][field])
			else:
				self.log('Unknown field: ' + field)
				columns.append(field)
		for row in rows[1:]:
			if "Missing Search" in row[0]:
				self.log('Bugzilla error (Missing search found)')
				return None
			fields = {}
			for i in range(min(len(row), len(columns))):
				fields[columns[i]] = row[i]
			results.append(fields)
		return results

	def search(self, query, comments = False, order = 'number',
			assigned_to = None, reporter = None, cc = None,
			commenter = None, whiteboard = None, keywords = None,
			status = [], severity = [], priority = [], product = [],
			component = []):
		"""Search bugzilla for a bug.

		@param query: query string to search in title or {comments}.
		@type  query: string
		@param order: what order to returns bugs in.
		@type  order: string

		@keyword assigned_to: email address which the bug is assigned to.
		@type    assigned_to: string
		@keyword reporter: email address matching the bug reporter.
		@type    reporter: string
		@keyword cc: email that is contained in the CC list
		@type    cc: string
		@keyword commenter: email of a commenter.
		@type    commenter: string

		@keyword whiteboard: string to search in status whiteboard (gentoo?)
		@type    whiteboard: string
		@keyword keywords: keyword to search for
		@type    keywords: string

		@keyword status: bug status to match. default is ['NEW', 'ASSIGNED',
						 'REOPENED'].
		@type    status: list
		@keyword severity: severity to match, empty means all.
		@type    severity: list
		@keyword priority: priority levels to patch, empty means all.
		@type    priority: list
		@keyword comments: search comments instead of just bug title.
		@type    comments: bool
		@keyword product: search within products. empty means all.
		@type    product: list
		@keyword component: search within components. empty means all.
		@type    component: list

		@return: list of bugs, each bug represented as a dict
		@rtype: list of dicts
		"""

		if not self.authenticated and not self.skip_auth:
			self.auth()

		qparams = config.params['list'].copy()
		if comments:
			qparams['long_desc'] = query
		else:
			qparams['short_desc'] = query

		qparams['order'] = config.choices['order'].get(order, 'Bug Number')
		qparams['bug_severity'] = severity or []
		qparams['priority'] = priority or []
		if status == None:
			qparams['bug_status'] = ['NEW', 'ASSIGNED', 'REOPENED']
		elif [s.upper() for s in status] == ['ALL']:
			qparams['bug_status'] = config.choices['status']
		else:
			qparams['bug_status'] = [s.upper() for s in status]
		qparams['product'] = product or ''
		qparams['component'] = component or ''
		qparams['status_whiteboard'] = whiteboard or ''
		qparams['keywords'] = keywords or ''

		# hoops to jump through for emails, since there are
		# only two fields, we have to figure out what combinations
		# to use if all three are set.
		unique = list(set([assigned_to, cc, reporter, commenter]))
		unique = [u for u in unique if u]
		if len(unique) < 3:
			for i in range(len(unique)):
				e = unique[i]
				n = i + 1
				qparams['email%d' % n] = e
				qparams['emailassigned_to%d' % n] = int(e == assigned_to)
				qparams['emailreporter%d' % n] = int(e == reporter)
				qparams['emailcc%d' % n] = int(e == cc)
				qparams['emaillongdesc%d' % n] = int(e == commenter)
		else:
			raise AssertionError('Cannot set assigned_to, cc, and '
					'reporter in the same query')

		req_params = urlencode(qparams, True)
		req_url = urljoin(self.base, config.urls['list'])
		req_url += '?' + req_params
		req = Request(req_url, None, config.headers)
		if self.httpuser and self.httppassword:
			base64string = base64.encodestring('%s:%s' % (self.httpuser, self.httppassword))[:-1]
			req.add_header("Authorization", "Basic %s" % base64string)
		resp = self.opener.open(req)
		return self.extractResults(resp)

	def namedcmd(self, cmd):
		"""Run command stored in Bugzilla by name.

		@return: Result from the stored command.
		@rtype: list of dicts
		"""

		if not self.authenticated and not self.skip_auth:
			self.auth()

		qparams = config.params['namedcmd'].copy()
		# Is there a better way of getting a command with a space in its name
		# to be encoded as foo%20bar instead of foo+bar or foo%2520bar?
		qparams['namedcmd'] = quote(cmd)
		req_params = urlencode(qparams, True)
		req_params = req_params.replace('%25','%')

		req_url = urljoin(self.base, config.urls['list'])
		req_url += '?' + req_params
		req = Request(req_url, None, config.headers)
		if self.user and self.hpassword:
			base64string = base64.encodestring('%s:%s' % (self.user, self.hpassword))[:-1]
			req.add_header("Authorization", "Basic %s" % base64string)
		resp = self.opener.open(req)

		return self.extractResults(resp)

	def get(self, bugid):
		"""Get an ElementTree representation of a bug.

		@param bugid: bug id
		@type  bugid: int

		@rtype: ElementTree
		"""
		if not self.authenticated and not self.skip_auth:
			self.auth()

		qparams = config.params['show'].copy()
		qparams['id'] = bugid

		req_params = urlencode(qparams, True)
		req_url = urljoin(self.base,  config.urls['show'])
		req_url += '?' + req_params
		req = Request(req_url, None, config.headers)
		if self.httpuser and self.httppassword:
			base64string = base64.encodestring('%s:%s' % (self.httpuser, self.httppassword))[:-1]
			req.add_header("Authorization", "Basic %s" % base64string)
		resp = self.opener.open(req)

		fd = StringIO(resp.read())

		# workaround for ill-defined XML templates in bugzilla 2.20.2
		(major_version, minor_version) = \
		    (sys.version_info[0], sys.version_info[1])
		if major_version > 2 or \
			    (major_version == 2 and minor_version >= 7):
			# If this is 2.7 or greater, then XMLTreeBuilder
			# does what we want.
			parser_class = ElementTree.XMLParser
		else:
			# Running under Python 2.6, so we need to use our
			# subclass of XMLTreeBuilder instead.
			parser_class = ForcedEncodingXMLTreeBuilder
		parser = parser_class(encoding = 'utf-8')

		etree = ElementTree.parse(fd, parser)
		bug = etree.find('.//bug')
		if bug and bug.attrib.has_key('error'):
			return None
		else:
			return etree

	def modify(self, bugid, title = None, comment = None, url = None,
			status = None, resolution = None,
			assigned_to = None, duplicate = 0,
			priority = None, severity = None,
			add_cc = [], remove_cc = [],
			add_dependson = [], remove_dependson = [],
			add_blocked = [], remove_blocked = [],
			whiteboard = None, keywords = None):
		"""Modify an existing bug

		@param bugid: bug id
		@type  bugid: int
		@keyword title: new title for bug
		@type    title: string
		@keyword comment: comment to add
		@type    comment: string
		@keyword url: new url
		@type    url: string
		@keyword status: new status (note, if you are changing it to RESOLVED, you need to set {resolution} as well.
		@type    status: string
		@keyword resolution: new resolution (if status=RESOLVED)
		@type    resolution: string
		@keyword assigned_to: email (needs to exist in bugzilla)
		@type    assigned_to: string
		@keyword duplicate: bug id to duplicate against (if resolution = DUPLICATE)
		@type    duplicate: int
		@keyword priority: new priority for bug
		@type    priority: string
		@keyword severity: new severity for bug
		@type    severity: string
		@keyword add_cc: list of emails to add to the cc list
		@type    add_cc: list of strings
		@keyword remove_cc: list of emails to remove from cc list
		@type    remove_cc: list of string.
		@keyword add_dependson: list of bug ids to add to the depend list
		@type    add_dependson: list of strings
		@keyword remove_dependson: list of bug ids to remove from depend list
		@type    remove_dependson: list of strings
		@keyword add_blocked: list of bug ids to add to the blocked list
		@type    add_blocked: list of strings
		@keyword remove_blocked: list of bug ids to remove from blocked list
		@type    remove_blocked: list of strings

		@keyword whiteboard: set status whiteboard
		@type    whiteboard: string
		@keyword keywords: set keywords
		@type    keywords: string

		@return: list of fields modified.
		@rtype: list of strings
		"""
		if not self.authenticated and not self.skip_auth:
			self.auth()


		buginfo = Bugz.get(self, bugid)
		if not buginfo:
			return False

		modified = []
		qparams = config.params['modify'].copy()
		qparams['id'] = bugid
		qparams['knob'] = 'none'

		# copy existing fields
		FIELDS = ('bug_file_loc', 'bug_severity', 'short_desc', 'bug_status',
				'status_whiteboard', 'keywords',
				'op_sys', 'priority', 'version', 'target_milestone',
				'assigned_to', 'rep_platform', 'product', 'component', 'token')

		FIELDS_MULTI = ('blocked', 'dependson')

		for field in FIELDS:
			try:
				qparams[field] = buginfo.find('.//%s' % field).text
			except:
				pass

		for field in FIELDS_MULTI:
			qparams[field] = [d.text for d in buginfo.findall('.//%s' % field)]

		# set 'knob' if we are change the status/resolution
		# or trying to reassign bug.
		if status:
			status = status.upper()
		if resolution:
			resolution = resolution.upper()

		if status == 'RESOLVED' and status != qparams['bug_status']:
			qparams['knob'] = 'resolve'
			if resolution:
				qparams['resolution'] = resolution
			else:
				qparams['resolution'] = 'FIXED'

			modified.append(('status', status))
			modified.append(('resolution', qparams['resolution']))
		elif status == 'ASSIGNED' and status != qparams['bug_status']:
			qparams['knob'] = 'accept'
			modified.append(('status', status))
		elif status == 'REOPENED' and status != qparams['bug_status']:
			qparams['knob'] = 'reopen'
			modified.append(('status', status))
		elif status == 'VERIFIED' and status != qparams['bug_status']:
			qparams['knob'] = 'verified'
			modified.append(('status', status))
		elif status == 'CLOSED' and status != qparams['bug_status']:
			qparams['knob'] = 'closed'
			modified.append(('status', status))
		elif duplicate:
			qparams['knob'] = 'duplicate'
			qparams['dup_id'] = duplicate
			modified.append(('status', 'RESOLVED'))
			modified.append(('resolution', 'DUPLICATE'))
		elif assigned_to:
			qparams['knob'] = 'reassign'
			qparams['assigned_to'] = assigned_to
			modified.append(('assigned_to', assigned_to))

		# setup modification of other bits
		if comment:
			qparams['comment'] = comment
			modified.append(('comment', ellipsis(comment, 60)))
		if title:
			qparams['short_desc'] = title or ''
			modified.append(('title', title))
		if url != None:
			qparams['bug_file_loc'] = url
			modified.append(('url', url))
		if severity != None:
			qparams['bug_severity'] = severity
			modified.append(('severity', severity))
		if priority != None:
			qparams['priority'] = priority
			modified.append(('priority', priority))

		# cc manipulation
		if add_cc != None:
			qparams['newcc'] = ', '.join(add_cc)
			modified.append(('newcc', qparams['newcc']))
		if remove_cc != None:
			qparams['cc'] = remove_cc
			qparams['removecc'] = 'on'
			modified.append(('cc', remove_cc))

		# bug depend/blocked manipulation
		changed_dependson = False
		changed_blocked = False
		if remove_dependson:
			for bug_id in remove_dependson:
				qparams['dependson'].remove(str(bug_id))
				changed_dependson = True
		if remove_blocked:
			for bug_id in remove_blocked:
				qparams['blocked'].remove(str(bug_id))
				changed_blocked = True
		if add_dependson:
			for bug_id in add_dependson:
				qparams['dependson'].append(str(bug_id))
				changed_dependson = True
		if add_blocked:
			for bug_id in add_blocked:
				qparams['blocked'].append(str(bug_id))
				changed_blocked = True

		qparams['dependson'] = ','.join(qparams['dependson'])
		qparams['blocked'] = ','.join(qparams['blocked'])
		if changed_dependson:
			modified.append(('dependson', qparams['dependson']))
		if changed_blocked:
			modified.append(('blocked', qparams['blocked']))

		if whiteboard != None:
			qparams['status_whiteboard'] = whiteboard
			modified.append(('status_whiteboard', whiteboard))
		if keywords != None:
			qparams['keywords'] = keywords
			modified.append(('keywords', keywords))

		req_params = urlencode(qparams, True)
		req_url = urljoin(self.base, config.urls['modify'])
		req = Request(req_url, req_params, config.headers)
		if self.httpuser and self.httppassword:
			base64string = base64.encodestring('%s:%s' % (self.httpuser, self.httppassword))[:-1]
			req.add_header("Authorization", "Basic %s" % base64string)

		try:
			resp = self.opener.open(req)
			re_error = re.compile(r'id="error_msg".*>([^<]+)<')
			error = re_error.search(resp.read())
			if error:
				print error.group(1)
				return []
			return modified
		except:
			return []

	def attachment(self, attachid):
		"""Get an attachment by attachment_id

		@param attachid: attachment id
		@type  attachid: int

		@return: dict with three keys, 'filename', 'size', 'fd'
		@rtype: dict
		"""
		if not self.authenticated and not self.skip_auth:
			self.auth()

		qparams = config.params['attach'].copy()
		qparams['id'] = attachid

		req_params = urlencode(qparams, True)
		req_url = urljoin(self.base, config.urls['attach'])
		req_url += '?' + req_params
		req = Request(req_url, None, config.headers)
		if self.httpuser and self.httppassword:
			base64string = base64.encodestring('%s:%s' % (self.httpuser, self.httppassword))[:-1]
			req.add_header("Authorization", "Basic %s" % base64string)
		resp = self.opener.open(req)

		try:
			content_type = resp.info()['Content-type']
			namefield = content_type.split(';')[1]
			filename = re.search(r'name=\"(.*)\"', namefield).group(1)
			content_length = int(resp.info()['Content-length'], 0)
			return {'filename': filename, 'size': content_length, 'fd': resp}
		except:
			return {}

	def post(self, product, component, title, description, url = '', assigned_to = '', cc = '', keywords = '', version = '', dependson = '', blocked = '', priority = '', severity = ''):
		"""Post a bug

		@param product: product where the bug should be placed
		@type product: string
		@param component: component where the bug should be placed
		@type component: string
		@param title: title of the bug.
		@type  title: string
		@param description: description of the bug
		@type  description: string
		@keyword url: optional url to submit with bug
		@type url: string
		@keyword assigned_to: optional email to assign bug to
		@type assigned_to: string.
		@keyword cc: option list of CC'd emails
		@type: string
		@keyword keywords: option list of bugzilla keywords
		@type: string
		@keyword version: version of the component
		@type: string
		@keyword dependson: bugs this one depends on
		@type: string
		@keyword blocked: bugs this one blocks
		@type: string
		@keyword priority: priority of this bug
		@type: string
		@keyword severity: severity of this bug
		@type: string

		@rtype: int
		@return: the bug number, or 0 if submission failed.
		"""
		if not self.authenticated and not self.skip_auth:
			self.auth()

		qparams = config.params['post'].copy()
		qparams['product'] = product
		qparams['component'] = component
		qparams['short_desc'] = title
		qparams['comment'] = description
		qparams['assigned_to']  = assigned_to
		qparams['cc'] = cc
		qparams['bug_file_loc'] = url
		qparams['dependson'] = dependson
		qparams['blocked'] = blocked
		qparams['keywords'] = keywords

		#XXX: default version is 'unspecified'
		if version != '':
			qparams['version'] = version

		#XXX: default priority is 'P2'
		if priority != '':
			qparams['priority'] = priority

		#XXX: default severity is 'normal'
		if severity != '':
			qparams['bug_severity'] = severity

		req_params = urlencode(qparams, True)
		req_url = urljoin(self.base, config.urls['post'])
		req = Request(req_url, req_params, config.headers)
		if self.httpuser and self.httppassword:
			base64string = base64.encodestring('%s:%s' % (self.httpuser, self.httppassword))[:-1]
			req.add_header("Authorization", "Basic %s" % base64string)
		resp = self.opener.open(req)

		try:
			re_bug = re.compile(r'<title>.*Bug ([0-9]+) Submitted</title>')
			bug_match = re_bug.search(resp.read())
			if bug_match:
				return int(bug_match.group(1))
		except:
			pass

		return 0

	def attach(self, bugid, title, description, filename,
			content_type = 'text/plain'):
		"""Attach a file to a bug.

		@param bugid: bug id
		@type  bugid: int
		@param title: short description of attachment
		@type  title: string
		@param description: long description of the attachment
		@type  description: string
		@param filename: filename of the attachment
		@type  filename: string
		@keywords content_type: mime-type of the attachment
		@type content_type: string

		@rtype: bool
		@return: True if successful, False if not successful.
		"""
		if not self.authenticated and not self.skip_auth:
			self.auth()

		qparams = config.params['attach_post'].copy()
		qparams['bugid'] = bugid
		qparams['description'] = title
		qparams['comment'] = description
		qparams['contenttypeentry'] = content_type

		filedata = [('data', filename, open(filename).read())]
		content_type, body = encode_multipart_formdata(qparams.items(),
				filedata)

		req_headers = config.headers.copy()
		req_headers['Content-type'] = content_type
		req_headers['Content-length'] = len(body)
		req_url = urljoin(self.base, config.urls['attach_post'])
		req = Request(req_url, body, req_headers)
		if self.httpuser and self.httppassword:
			base64string = base64.encodestring('%s:%s' % (self.httpuser, self.httppassword))[:-1]
			req.add_header("Authorization", "Basic %s" % base64string)
		resp = self.opener.open(req)

		# TODO: return attachment id and success?
		try:
			re_success = re.compile(r'<title>Changes Submitted</title>')
			if re_success.search(resp.read()):
				return True
		except:
			pass

		return False
