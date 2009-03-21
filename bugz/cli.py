#!/usr/bin/env python

import commands
import locale
import os
import re
import readline
import tempfile

from optparse import BadOptionError, OptionParser,  make_option
from urlparse import urljoin

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

#
# Bugz specific exceptions
#

class BugzError(Exception):
    pass

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
# ugly optparse callbacks (really need to integrate this somehow)
#

def modify_opt_fixed(opt, opt_str, val, parser):
    parser.values.status = 'RESOLVED'
    parser.values.resolution = 'FIXED'

def modify_opt_invalid(opt, opt_str, val, parser):
    parser.values.status = 'RESOLVED'
    parser.values.resolution = 'INVALID'

class PrettyBugz(Bugz):
    options = {
        'base': make_option('-b', '--base', type='string',
                            default = 'https://bugs.gentoo.org/',
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

    def post(self, product = None, component = None, title = None, description = None, assigned_to = None,
             cc = None, url = None, keywords = None, emerge_info = False,
             description_from = None, version = None, append_command = None):
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
        if version is None:
            version = self.get_input('Enter version (default: unspecified): ')
        else:
            self.log('Enter version: %s' % version)

        # check for title
        if not title:
            while not title or len(title) < 1:
                title = self.get_input('Enter title: ')
        else:
            self.log('Enter title: %s' % title)

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
            self.log('Enter bug description: %s)' % description)

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

        # check for Keywords list
        if keywords is None:
            kwd_msg = 'Enter a Keywords list (comma separated) (optional):'
            keywords = self.get_input(kwd_msg)
        else:
            self.log('Enter a Keywords list (optional): %s' % keywords)

        # print submission confirmation
        print '-' * (self.columns - 1)
        print 'Product     : ' + product
        print 'Component   : ' + component
        print 'Version     : ' + version
        print 'Title       : ' + title
        print 'URL         : ' + url
        print 'Assigned to : ' + assigned_to
        print 'CC          : ' + cc
        print 'Keywords    : ' + keywords
        print 'Description : ' + description
        print '-' * (self.columns - 1)

        #FIXME: Remove in 0.8
        if emerge_info is True:
            self.warn('--emerge-info is deprecated. Please, use --append-command.')
            append_command = 'emerge --ignore-default-opts --info'

        if append_command is None:
            append_command = self.get_input('Append the output of the following command (leave blank for none): ')
        else:
            self.log('Append command (optional): %s' % append_command)

        if append_command is not None and append_command != '':
            import commands
            append_command_output = commands.getoutput(append_command)
            description = description + '\n\n' + '$ ' + append_command + '\n' +  append_command_output

        confirm = raw_input('Confirm bug submission (y/N)?')
        if len(confirm) < 1 or confirm[0] not in ('y', 'Y'):
            self.log('Submission aborted')
            return


        result = Bugz.post(self, product, component, title, description, url, assigned_to, cc, keywords, version)
        if result != None:
            self.log('Bug %d submitted' % result)
        else:
            raise RuntimeError('Failed to submit bug')

    post.args = "[options]"
    post.options = {
        'product': make_option('--product', help = 'Product'),
        'component': make_option('--component', help = 'Component'),
        'version': make_option('--version', help = 'Version of the component'),
        'title': make_option('-t', '--title', help = 'Title of bug'),
        'description': make_option('-d', '--description',
                                   help = 'Description of the bug'),
        'description_from': make_option('-F' , '--description-from',
                                        help = 'Description from contents of'
                                        ' file'),
        'emerge_info': make_option('-e', '--emerge-info', action="store_true",
                                   help = 'Include emerge --info (DEPRECATED, use --append-command)'),
        'append_command': make_option('--append-command',
                                      help = 'Append the output of a command to the description.'),
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
