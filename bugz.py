#!/usr/bin/env python

"""
Python Bugzilla Interface

Simple command-line interface to bugzilla to allow:
 - searching
 - getting bug info
 - saving attachments

Requirements
------------
 - Python 2.4 or later
 - ElementTree (only for Python 2.4)

Classes
-------
 - Bugz - Pythonic interface to Bugzilla
 - PrettyBugz - Command line interface to Bugzilla

"""

__version__ = '0.7.1'
__author__ = 'Alastair Tse <http://www.liquidx.net/>'
__contributors__ = []
__revision__ = '$Id: $'
__license__ = """Copyright (c) 2006, Alastair Tse, All rights reserved.
This following source code is licensed under the GPL v2 License."""

BUGZ_USER_AGENT = 'PyBugz/%s +http://www.liquidx.net/' % __version__
BUGZ_COMMENT_TEMPLATE = \
"""
BUGZ: ---------------------------------------------------
%s
BUGZ: Any line beginning with 'BUGZ:' will be ignored.
BUGZ: ---------------------------------------------------
"""

EMERGE = "/usr/bin/emerge"
COOKIE_FILE = '.bugz_cookie'
CONFIG_FILE = '.bugz'
DEFAULT_NUM_COLS = 80


class BugzConfig:
    urls = {
        'auth': 'index.cgi',
        'list': 'buglist.cgi',
        'show': 'show_bug.cgi',
        'attach': 'attachment.cgi',
        'post': 'post_bug.cgi',
        'modify': 'process_bug.cgi',
        'attach_post': 'attachment.cgi',
    }

    headers = {
        'Accept': '*/*',
        'User-agent': BUGZ_USER_AGENT,
    }

    params = {
        'auth': {
        "Bugzilla_login": "",
        "Bugzilla_password": "",
        "GoAheadAndLogIn": "1",
        },

        'post': {
        'product': 'Gentoo Linux',
        'version': 'unspecified',
        'rep_platform': 'All',
        'op_sys': 'Linux',
        'priority': 'P3',
        'bug_severity': 'enhancement',
        'bug_status': 'NEW',
        'assigned_to': '',
        'keywords': '',
        'dependson':'',
        'blocked':'',
        'component': 'Ebuilds',
        # needs to be filled in
        'bug_file_loc': '',
        'short_desc': '',
        'comment': '',
        },

        'attach': {
        'id':''
        },

        'attach_post': {
        'action': 'insert',
        'contenttypemethod': 'manual',
        'bugid': '',
        'description': '',
        'contenttypeentry': 'text/plain',
        'comment': '',
        },

        'show': {
        'id': '',
        'ctype': 'xml'
        },

        'list': {
        'query_format': 'advanced',
        'short_desc_type': 'allwordssubstr',
        'short_desc': '',
        'long_desc_type': 'substring',
        'long_desc' : '',
        'bug_file_loc_type': 'allwordssubstr',
        'bug_file_loc': '',
        'status_whiteboard_type': 'allwordssubstr',
        'status_whiteboard': '',
        'bug_status': ['NEW', 'ASSIGNED', 'REOPENED'],
        'bug_severity': [],
        'priority': [],
        'emaillongdesc1': '1',
        'emailassigned_to1':'1',
        'emailtype1': 'substring',
        'email1': '',
        'emaillongdesc2': '1',
        'emailassigned_to2':'1',
        'emailreporter2':'1',
        'emailcc2':'1',
        'emailtype2':'substring',
        'email2':'',
        'bugidtype':'include',
        'bug_id':'',
        'chfieldfrom':'',
        'chfieldto':'Now',
        'chfieldvalue':'',
        'cmdtype':'doit',
        'order': 'Bug Number',
        'field0-0-0':'noop',
        'type0-0-0':'noop',
        'value0-0-0':'',
        'ctype':'csv',
        },

        'modify': {
        #    'delta_ts': '%Y-%m-%d %H:%M:%S',
        'longdesclength': '1',
        'id': '',
        'newcc': '',
        'removecc': '',  # remove selected cc's if set
        'cc': '',        # only if there are already cc's
        'bug_file_loc': '',
        'bug_severity': '',
        'bug_status': '',
        'op_sys': '',
        'priority': '',
        'version': '',
        'target_milestone': '',
        'rep_platform': '',
        'product':'',
        'component': '',
        'short_desc': '',
        'status_whiteboard': '',
        'keywords': '',
        'dependson': '',
        'blocked': '',
        'knob': ('none', 'assigned', 'resolve', 'duplicate', 'reassign'),
        'resolution': '', # only valid for knob=resolve
        'dup_id': '',     # only valid for knob=duplicate
        'assigned_to': '',# only valid for knob=reassign
        'form_name': 'process_bug',
        'comment':''
        }

    }

    choices = {
        'status': {
        'unconfirmed': 'UNCONFIRMED',
        'new': 'NEW',
        'assigned': 'ASSIGNED',
        'reopened': 'REOPENED',
        'resolved': 'RESOLVED',
        'verified': 'VERIFIED',
        'closed':   'CLOSED'
        },

        'order': {
        'number' : 'Bug Number',
        'assignee': 'Assignee',
        'importance': 'Importance',
        'date': 'Last Changed'
        },

        'columns': [
        'bugid',
        'alias',
        'severity',
        'priority',
        'arch',
        'assignee',
        'status',
        'resolution',
        'desc'
        ],

        'column_alias': {
        'bug_id': 'bugid',
        'alias': 'alias',
        'bug_severity': 'severity',
        'priority': 'priority',
        'op_sys': 'arch', #XXX: Gentoo specific?
        'assigned_to': 'assignee',
        'assigned_to_realname': 'assignee', #XXX: Distinguish from assignee?
        'bug_status': 'status',
        'resolution': 'resolution',
        'short_desc': 'desc',
        'short_short_desc': 'desc',
        },
        # Novell: bug_id,"bug_severity","priority","op_sys","bug_status","resolution","short_desc"
        # Gentoo: bug_id,"bug_severity","priority","op_sys","assigned_to","bug_status","resolution","short_short_desc"
        # Redhat: bug_id,"alias","bug_severity","priority","rep_platform","assigned_to","bug_status","resolution","short_short_desc"
        # Mandriva: 'bug_id', 'bug_severity', 'priority', 'assigned_to_realname', 'bug_status', 'resolution', 'keywords', 'short_desc'

        'resolution': {
        'fixed': 'FIXED',
        'invalid': 'INVALID',
        'duplicate': 'DUPLICATE',
        'lated': 'LATER',
        'needinfo': 'NEEDINFO',
        'wontfix': 'WONTFIX',
        'upstream': 'UPSTREAM',
        },

        'severity': [
        'blocker',
        'critical',
        'major',
        'normal',
        'minor',
        'trivial',
        'enhancement',
        ],

        'priority': {
        1:'P1',
        2:'P2',
        3:'P3',
        4:'P4',
        5:'P5',
        }

    }

import csv
import os
import re
import mimetypes
import locale
import commands
import base64
import readline

from optparse import OptionParser, make_option, BadOptionError
from cStringIO import StringIO
from urlparse import urlsplit, urljoin
from urllib import urlencode
from urllib2 import build_opener, HTTPCookieProcessor, Request
from cookielib import LWPCookieJar, CookieJar

try:
    # Python standard library implementation
    from xml.etree import ElementTree
except ImportError:
    # Old stand-alone implementation
    from elementtree import ElementTree

#
# Global configuration
#

try:
    config
except NameError:
    config = BugzConfig()

#
# Auxillary functions
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

def which(cmd):
    """ just like /usr/bin/which, but in 5 lines of python.

    @return: full path of the executable
    @rtype: string or None
    """
    paths = os.environ['PATH'].split(':')
    for path in paths:
        if os.access(os.path.join(path, cmd), os.X_OK):
            return os.path.join(path, cmd)
    return None

def get_cols():
    """ get the number of columns in the terminal.

    @return: width of the current terminal
    @rtype: int
    """
    stty = which('stty')
    if stty:
        row_cols = commands.getoutput("%s size" % stty)
        rows, cols = map(int, row_cols.split())
        return cols
    else:
        return DEFAULT_NUM_COLS

def launch_editor(initial_text, comment_prefix = 'BUGZ:'):
    """Launch an editor with some default text.

    Lifted from Mercurial 0.9.
    @rtype: string
    """
    import tempfile
    (fd, name) = tempfile.mkstemp("bugz")
    f = os.fdopen(fd, "w")
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

def block_edit(comment):
    editor = (os.environ.get('BUGZ_EDITOR') or
              os.environ.get('EDITOR'))

    if not editor:
        print comment + ': (Press Ctrl+D to end)'
        new_text = raw_input_block()
        return new_text

    initial_text = '\n'.join(['BUGZ: %s'%line for line in comment.split('\n')])
    new_text = launch_editor(BUGZ_COMMENT_TEMPLATE % initial_text)

    if new_text.strip():
        return new_text
    else:
        return ''

def ellipsis(text, length):
    if len(text) > length:
        return text[:length-4] + "..."
    else:
        return text

#
# Override the behaviour of elementtree and allow us to
# force the encoding to ISO-8859-1
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
# LaxOptionParser will silently ignore options that it does not
# recognise, as opposed to OptionParser which will throw an
# exception.
#

class LaxOptionParser(OptionParser):
    def _match_long_opt(self, opt):
        try:
            return OptionParser._match_long_opt(self, opt)
        except BadOptionError, e:
            raise KeyError

    def _process_short_opts(self, rargs, values):
        arg = rargs.pop(0)
        stop = False
        i = 1
        for ch in arg[1:]:
            opt = "-" + ch
            option = self._short_opt.get(opt)
            i += 1                      # we have consumed a character

            if not option:
                raise KeyError
            if option.takes_value():
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    rargs.insert(0, arg[i:])
                    stop = True

                nargs = option.nargs
                if len(rargs) < nargs:
                    if nargs == 1:
                        self.error("%s option requires an argument" % opt)
                    else:
                        self.error("%s option requires %d arguments"
                                   % (opt, nargs))
                elif nargs == 1:
                    value = rargs.pop(0)
                else:
                    value = tuple(rargs[0:nargs])
                    del rargs[0:nargs]

            else:                       # option doesn't take a value
                value = None

            option.process(opt, value, values, self)

            if stop:
                break

    def _process_args(self, largs, rargs, values):
        while rargs:
            arg = rargs[0]
            if arg == '--':
                del rargs[0]
                return
            elif arg[0:2] == '--':
                try:
                    self._process_long_opt(rargs, values)
                except KeyError, e:
                    if '=' in arg:
                        rargs.pop(0)
                    largs.append(arg) # popped from rarg in _process_long_opt
            elif arg[:1] == '-' and len(arg) > 1:
                try:
                    self._process_short_opts(rargs, values)
                except KeyError, e:
                    largs.append(arg) # popped from rarg in _process_short_opt
            elif self.allow_interspersed_args:
                largs.append(arg)
                del rargs[0]
            else:
                return

#
# Bugz specific exceptions
#

class BugzError(Exception):
    pass

#
# ugly optparse callbacks (really need to integrate this somehow)
#

def modify_opt_fixed(opt, opt_str, val, parser):
    parser.values.status = 'RESOLVED'
    parser.values.resolution = 'FIXED'

def modify_opt_invalid(opt, opt_str, val, parser):
    parser.values.status = 'RESOLVED'
    parser.values.resolution = 'INVALID'


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
                 always_auth = False, httpuser = None, httppassword = None ):
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
        @keyword always_auth: authenticate on every command
        @type    always_auth: bool
        """
        self.base = base
        scheme, self.host, self.path, query, frag  = urlsplit(self.base)
        self.authenticated = False

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

        self.opener = build_opener(HTTPCookieProcessor(self.cookiejar))
        self.user = user
        self.password = password
        self.httpuser = httpuser
        self.httppassword = httppassword
        self.forget = forget
        self.always_auth = always_auth

        if always_auth:
            self.auth()

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
        re_request_login = re.compile(r'<title>.*Log in to Bugzilla</title>')
        if not re_request_login.search(resp.read()):
            self.log('Already logged in.')
            self.authenticated = True
            return

        # prompt for username and password if we were not supplied with it
        if not self.user or not self.password:
            import getpass
            self.log('No username or password given.')
            self.user = self.get_input('Username: ')
            self.password = getpass.getpass()

        # perform login
        qparams = config.params['auth'].copy()
        qparams['Bugzilla_login'] = self.user
        qparams['Bugzilla_password'] = self.password

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
            fields = {}
            for i in range(min(len(row), len(columns))):
                fields[columns[i]] = row[i]
            results.append(fields)

        return results

    def get(self, bugid):
        """Get an ElementTree representation of a bug.

        @param bugid: bug id
        @type  bugid: int

        @rtype: ElementTree
        """
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
        parser = ForcedEncodingXMLTreeBuilder(encoding = 'ISO-8859-1')
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
        if not self.authenticated:
            self.auth()


        buginfo = Bugz.get(self, bugid)
        if not buginfo:
            return False

        import time
        modified = []
        qparams = config.params['modify'].copy()
        qparams['id'] = bugid
        qparams['knob'] = 'none'

        # copy existing fields
        FIELDS = ('bug_file_loc', 'bug_severity', 'short_desc', 'bug_status',
                  'status_whiteboard', 'keywords',
                  'op_sys', 'priority', 'version', 'target_milestone',
                  'assigned_to', 'rep_platform', 'product', 'component')

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

    def post(self, title, description, url = '', assigned_to = '', cc = '', keywords = ''):
        """Post a bug

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

        @rtype: int
        @return: the bug number, or 0 if submission failed.
        """
        if not self.authenticated:
            self.auth()

        qparams = config.params['post'].copy()
        qparams['short_desc'] = title
        qparams['comment'] = description
        qparams['assigned_to']  = assigned_to
        qparams['cc'] = cc
        qparams['bug_file_loc'] = url
        qparams['keywords'] = keywords

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
        if not self.authenticated:
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

class PrettyBugz(Bugz):
    options = {
        'base': make_option('-b', '--base', type='string',
                            default = 'http://bugs.gentoo.org/',
                            help = 'Base URL of Bugzilla'),
        'user': make_option('-u', '--user', type='string',
                            help = 'Username for commands requiring authentication'),
        'password': make_option('-p', '--password', type='string',
                                help = 'Password for commands requiring authentication'),
        'httpuser': make_option('-H', '--httpuser', type='string',
                            help = 'Username for basic http auth'),
        'httppassword': make_option('-P', '--httppassword', type='string',
                                help = 'Password for basic http auth'),
        'forget': make_option('-f', '--forget', action='store_true',
                              help = 'Forget login after execution'),
        'columns': make_option('--columns', type='int', default = 0,
                               help = 'Maximum number of columns output should use'),
        'encoding': make_option('--encoding', 
                                help = 'Output encoding (default: utf-8).'),
        'always_auth': make_option('-A', '--always-auth', action='store_true',
                                   default = False,
                                   help = 'Authenticated for every command.'),
        'quiet': make_option('-q', '--quiet', action='store_true',
                             default = False, help = 'Quiet mode'),
    }

    def __init__(self, base, user = None, password =None, forget = False,
                 columns = 0, encoding = '', always_auth = False,
                 quiet = False, httpuser = None, httppassword = None ):

        self.quiet = quiet
        self.columns = columns or get_cols()

        Bugz.__init__(self, base, user, password, forget, always_auth, httpuser, httppassword)

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

    def search(self, *args, **kwds):
        """Performs a search on the bugzilla database with the keywords given on the title (or the body if specified).
        """
        search_term = ' '.join(args).strip()
        search_opts = sorted([(opt, val) for opt, val in kwds.items()
                              if val != None and opt != 'order'])

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

        if result == None:
            raise RuntimeError('Failed to perform search')

        if len(result) == 0:
            self.log('No bugs found.')
            return

        for row in result:
            desc = row['desc'][:self.columns - 30]
            if row.has_key('assignee'): # Novell does not have 'assignee' field
                assignee = row['assignee'].split('@')[0]
                print '%7s %-20s %s' % (row['bugid'], assignee, desc)
            else:
                print '%7s %s' % (row['bugid'], desc)

    search.args = "<search term> [options..]"
    search.options = {
        'order': make_option('-o', '--order', type='choice',
                             choices = config.choices['order'].keys(),
                             default = 'number'),
        'assigned_to': make_option('-a', '--assigned-to',
                                help = 'email the bug is assigned to'),
        'reporter': make_option('-r', '--reporter',
                                   help = 'email the bug was reported by'),
        'cc': make_option('--cc',help = 'Restrict by CC email address'),
        'commenter': make_option('--commenter',help = 'email that commented the bug'),
        'status': make_option('-s', '--status', action='append',
                              help = 'Bug status (for multiple choices,'
                              'use --status=NEW --status=ASSIGNED)'),
        'severity': make_option('--severity', action='append',
                                choices = config.choices['severity'],
                                help = 'Restrict by severity.'),
        'priority': make_option('--priority', action='append',
                                choices = config.choices['priority'].values(),
                                help = 'Restrict by priority (1 or more)'),
        'comments': make_option('-c', '--comments',  action='store_true',
                                help = 'Search comments instead of title'),
        'product': make_option('-P', '--product', action='append',
                                 help = 'Restrict by product (1 or more)'),
        'component': make_option('-C', '--component', action='append',
                                 help = 'Restrict by component (1 or more)'),
        'keywords': make_option('-k', '--keywords', help = 'Bug keywords'),
        'whiteboard': make_option('-w', '--whiteboard',
                                  help = 'Status whiteboard'),
    }


    def get(self, bugid, comments = True, attachments = True):
        """ Fetch bug details given the bug id """
        try:
            int(bugid)
        except ValueError:
            raise BugzError("bugid must be a number.")

        self.log('Getting bug %s ..' % bugid)

        result = Bugz.get(self, bugid)

        if result == None:
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
                value = result.find('//%s' % field).text
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

        bug_comments = result.findall('//long_desc')
        bug_attachments = result.findall('//attachment')

        print '%-12s: %d' % ('Comments', len(bug_comments))
        print '%-12s: %d' % ('Attachments', len(bug_attachments))
        print '%-12s: %s' % ('URL', '%s?id=%s' % (urljoin(self.base,
                                                    config.urls['show']),
                                                    bugid))
        print

        if attachments:
            for attachment in bug_attachments:
                aid = attachment.find('.//attachid').text
                desc = attachment.find('.//desc').text
                when = attachment.find('.//date').text
                print '[Attachment] [%s] [%s]' % (aid, desc.encode(self.enc))

        if comments:
            import textwrap
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

                # print wrapped version
                for line in what.split('\n'):
                    if len(line) < self.columns:
                        print line.encode(self.enc)
                    else:
                        for shortline in wrapper.wrap(line):
                            print shortline.encode(self.enc)
                i += 1
            print

    get.args = "<bug_id> [options..]"
    get.options = {
        'comments': make_option("-n", "--no-comments", dest = 'comments',
                                action="store_false", default = True,
                                help = 'Do not show comments'),
    }

    def post(self, title = None, description = None, assigned_to = None,
             cc = None, url = None, keywords = None, emerge_info = None,
             description_from = None):
        """Post a new bug"""
        # As we are submitting something, we should really
        # grab entry from console rather than from the command line:
        if not self.authenticated:
            self.auth()

        self.log('Press Ctrl+C at any time to abort.')

        #
        #  Check all bug fields.
        #  XXX: We use "if not <field>" for mandatory fields
        #       and "if <field> is None" for optional ones.
        #

	# check for title
        if not title:
            while not title or len(title) < 1:
                title = self.get_input('Enter title: ')
        else:
            print 'Enter title:', title

        # load description from file if possible
        if description_from:
            try:
                description = open(description_from, 'r').read()
            except IOError, e:
                raise BugzError('Unable to read from file: %s: %s' % \
                                (description_from, e))

        # check for description
        if not description:
            description = block_edit('Enter bug description: ')
        else:
            print 'Enter bug description:'
            print description

        # check for optional URL
        if url is None:
            url = self.get_input('Enter URL (optional): ')
        else:
            self.log('Enter URL (optional): %s' % url)

        # check for default assignee
        if assigned_to is None:
            assigned_msg ='Enter assignee (eg. liquidx@gentoo.org) (optional):'
            assigned_to = self.get_input(assigned_msg)
        else:
            self.log('Enter assignee (optional): %s' % assigned_to)

        # check for CC list
        if cc is None:
            cc_msg = 'Enter a CC list (comma separated) (optional):'
            cc = self.get_input(cc_msg)
        else:
            self.log('Enter a CC list (optional): %s' % cc)

        # print submission confirmation
        print '-' * (self.columns - 1)
        print 'Title       : ' + title
        print 'URL         : ' + url
        print 'Assigned to : ' + assigned_to
        print 'CC          : ' + cc
        print 'Keywords    : ' + keywords
        print 'Description : '
        print description
        print '-' * (self.columns - 1)

        if emerge_info == None:
            ask_emerge = raw_input('Include output of emerge --info (Y/n)?')
            if ask_emerge[0] in ('y', 'Y'):
                emerge_info = True

        if emerge_info:
            import commands
            emerge_info_output = commands.getoutput('%s --info' % EMERGE)
            description = description + '\n' + emerge_info_output

        confirm = raw_input('Confirm bug submission (y/N)?')
        if confirm[0] not in ('y', 'Y'):
            self.log('Submission aborted')
            return


        result = Bugz.post(self, title, description, url, assigned_to, cc, keywords)
        if result != None:
            self.log('Bug %d submitted' % result)
        else:
            raise RuntimeError('Failed to submit bug')

    post.args = "[options]"
    post.options = {
        'title': make_option('-t', '--title', help = 'Title of bug'),
        'description': make_option('-d', '--description',
                                   help = 'Description of the bug'),
        'description_from': make_option('-F' , '--description-from',
                                        help = 'Description from contents of'
                                        ' file'),
        'emerge_info': make_option('-e', '--emerge-info', action="store_true",
                                   help = 'Include emerge --info'),
        'assigned_to': make_option('-a', '--assigned-to',
                                   help = 'Assign bug to someone other than '
                                   'the default assignee'),
        'cc': make_option('--cc', help = 'Add a list of emails to CC list'),
        'url': make_option('-U', '--url', 
                           help = 'URL associated with the bug'),
        'keywords': make_option('-k', '--keywords', help = 'List of bugzilla keywords'),
    }


    def modify(self, bugid, **kwds):
        """Modify an existing bug (eg. adding a comment or changing resolution.)"""
        if not self.authenticated:
            self.auth()

        if 'comment_from' in kwds:
            if kwds['comment_from']:
                try:
                    kwds['comment']  = open(kwds['comment_from'], 'r').read()
                except IOError, e:
                    raise BugzError('Failed to get read from file: %s: %s' % \
                                    (comment_from, e))

            del kwds['comment_from']

        if 'comment_editor' in kwds:
            if kwds['comment_editor']:
                kwds['comment'] = block_edit('Enter comment:')
            del kwds['comment_editor']

        result = Bugz.modify(self, bugid, **kwds)
        if not result:
            raise RuntimeError('Failed to modify bug')
        else:
            self.log('Modified bug %s with the following fields:' % bugid)
            for field, value in result:
                self.log('  %-12s: %s' % (field, value))


    modify.args = "<bug_id> [options..]"
    modify.options = {
        'title': make_option('-t', '--title', help = 'Set title of bug'),
        'comment_from': make_option('-F', '--comment-from',
                                    help = 'Add comment from file'),
        'comment_editor': make_option('-C', '--comment-editor',
                                      action='store_true', default = False,
                                      help = 'Add comment via default editor'),
        'comment': make_option('-c', '--comment', help = 'Add comment to bug'),
        'url': make_option('-U', '--url', help = 'Set URL field of bug'),
        'status': make_option('-s', '--status',
                              choices=config.choices['status'].values(),
                              help = 'Set new status of bug (eg. RESOLVED)'),
        'resolution': make_option('-r', '--resolution',
                                  choices=config.choices['resolution'].values(),
                                  help = 'Set new resolution (only if status = RESOLVED)'),
        'assigned_to': make_option('-a', '--assigned-to'),
        'duplicate': make_option('-d', '--duplicate', type='int', default=0),
        'priority': make_option('--priority', 
                                choices=config.choices['priority'].values()),
        'severity': make_option('-S', '--severity'),
        'fixed': make_option('--fixed', action='callback',
                             callback = modify_opt_fixed,
                             help = "Mark bug as RESOLVED, FIXED"),
        'invalid': make_option('--invalid', action='callback',
                               callback = modify_opt_invalid,
                               help = "Mark bug as RESOLVED, INVALID"),
        'add_cc': make_option('--add-cc', action = 'append',
                              help = 'Add an email to the CC list'),
        'remove_cc': make_option('--remove-cc', action = 'append',
                                 help = 'Remove an email from the CC list'),
        'add_dependson': make_option('--add-dependson', action = 'append',
                              help = 'Add a bug to the depends list'),
        'remove_dependson': make_option('--remove-dependson', action = 'append',
                                 help = 'Remove a bug from the blocked list'),
        'add_blocked': make_option('--add-blocked', action = 'append',
                              help = 'Add a bug to the blocked list'),
        'remove_blocked': make_option('--remove-blocked', action = 'append',
                                 help = 'Remove a bug from the blocked list'),
        'whiteboard': make_option('-w', '--whiteboard',
                                  help = 'Set Status whiteboard'),
        'keywords': make_option('-k', '--keywords',
                                help = 'Set bug keywords'),
        }

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

    attachment.args = "<attachid> [-v]"
    attachment.options = {
        'view': make_option('-v', '--view', action="store_true",
                            default = False,
                            help = "Print attachment rather that save")
    }

    def attach(self, bugid, filename, content_type = 'text/plain', description = None):
        """ Attach a file to a bug given a filename. """
        if not self.authenticated:
            self.auth()

        import os
        if not os.path.exists(filename):
            raise BugzError('File not found: %s' % filename)
        if not description:
            description = block_edit('Enter description (optional)')
        result = Bugz.attach(self, bugid, filename, description, filename,
                             content_type)

    attach.args = "<bugid> <filename> [-c=<mimetype>] [-d=<description>]"
    attach.options = {
        'content_type': make_option('-c', '--content_type',
                                    default='text/plain',
                                    help = 'Mimetype of the file (default: text/plain)'),
        'description': make_option('-d', '--description',
                                    help = 'A description of the attachment.')
    }

    @classmethod
    def usage(self, cmd = None):
        print 'Usage: bugz <subcommand> [parameter(s)] [options..]'
        print
        print 'Options:'
        print '  -b, --base <bugzilla_url>    Bugzilla base URL'
        print '  -u, --user <username>        User name (if required)'
        print '  -p, --password <password>    Password (if required)'
        print '  -H, --httpuser <username>       Basic http auth User name (if required)'
        print '  -P, --httppassword <password>   Basic http auth Password (if required)'
        print '  -f, --forget                 Do not remember authentication'
        print '  --columns <columns>          Number of columns to use when'
        print '                               displaying output'
        print '  -A, --always-auth            Authenticate on every command.'
        print '  -q, --quiet                  Do not display status messages.'
        print

        if cmd == None:
            print 'Subcommands:'
            print '  search      Search for bugs in bugzilla'
            print '  get         Get a bug from bugzilla'
            print '  attachment  Get an attachment from bugzilla'
            print '  post        Post a new bug into bugzilla'
            print '  modify      Modify a bug (eg. post a comment)'
            print '  attach      Attach file to a bug'
            print
            print 'Examples:'
            print '  bugz get 12345'
            print '  bugz search python --assigned-to liquidx@gentoo.org'
            print '  bugz attachment 5000 --view'
            print '  bugz attach 140574 python-2.4.3.ebuild'
            print '  bugz modify 140574 -c "Me too"'
            print
            print 'For more information on subcommands, run:'
            print '  bugz <subcommand> --help'
        else:
            try:
                cmd_options = getattr(self, cmd).options.values()
                cmd_args = getattr(self, cmd).args
                cmd_desc = getattr(self, cmd).__doc__
                """
                if getattr(PrettyBugz, cmd):
                    cmd_options = getattr(getattr(PrettyBugz, cmd),
                                          "options", {})
                    cmd_args = getattr(getattr(PrettyBugz, cmd),
                                       "args", "[options]")
                """
                parser = OptionParser(usage = '%%prog %s %s' % (cmd,cmd_args),
                                      description = cmd_desc,
                                      option_list = cmd_options)
                print 'Subcommand Options for %s:' % cmd
                parser.print_help()
            except:
                print 'Unknown subcommand: %s' % cmd


def main():
    import sys
    import getopt

    if len(sys.argv) < 2:
        PrettyBugz.usage()
        sys.exit(-1)

    try:
        # do one global option search first to find those options
        # that are global across all sub commands.
        global_opts = PrettyBugz.options
        global_parser = LaxOptionParser(option_list = global_opts.values(),
                                        add_help_option = False)

        gopts, gargs = global_parser.parse_args()
        cmd = gargs[0]

        # gather options
        cmd_options = {}
        cmd_args = ''
        cmd_func = getattr(PrettyBugz, cmd, None)

        if cmd_func:
            cmd_options = getattr(cmd_func, "options", {})
            cmd_args = getattr(cmd_func, "args", "[options]")
        else:
            print '!! Error: Unable to recognise command: %s' % cmd
            print
            PrettyBugz.usage()
            sys.exit(-1)

        # parse options
        parser = OptionParser(usage = '%%prog %s %s' % (cmd, cmd_args),
                              description = cmd_func.__doc__,
                              option_list = cmd_options.values())
        opts, args = parser.parse_args(gargs[1:])

        # separate bugz options and cmd options
        bugz_kwds = {}
        for name, opt in global_opts.items():
            try:
                bugz_kwds[name] = getattr(gopts, name)
            except AttributeError:
                pass

        cmd_kwds = {}
        for name, opt in cmd_options.items():
            try:
                cmd_kwds[name] = getattr(opts, name)
            except AttributeError:
                pass

        try:
            bugz = PrettyBugz(**bugz_kwds)
            getattr(bugz, cmd)(*args, **cmd_kwds)
        except BugzError, e:
            print ' ! Error: %s' % e
            print
            parser.print_help()
            sys.exit(-1)
        except TypeError, e:
            print ' ! Error: Incorrect number of arguments supplied'
            print
            import traceback
            traceback.print_exc()
            parser.print_help()
            sys.exit(-1)
        except RuntimeError, e:
            print ' ! Error: %s' % e
            sys.exit(-1)

    except KeyboardInterrupt:
        print
        print 'Stopped.'
    except:
        raise

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print '\n ! Exiting.'
