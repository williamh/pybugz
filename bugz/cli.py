"""
Python Bugzilla Interface

Simple command-line interface to bugzilla to allow:
 - searching
 - getting bug info
 - saving attachments

Requirements
------------
- Python 3.3 or later
- setuptools

Classes
-------
 - BugzillaProxy - Server proxy for communication with Bugzilla

"""

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


from bugz.bugtracker import BugTracker
from bugz.cli_argparser import make_arg_parser
from bugz.configfile import load_config
from bugz.settings import Settings
from bugz.exceptions import BugzError
from bugz.log import log_error, log_info
from bugz.utils import block_edit, get_content_type


def list_bugs(buglist, settings):
    for bug in buglist:
        bugid = bug['id']
        status = bug['status']
        priority = bug['priority']
        severity = bug['severity']
        assignee = bug['assigned_to'].split('@')[0]
        desc = bug['summary']
        line = '%s' % (bugid)
        if hasattr(settings, 'show_status'):
            line = '%s %-12s' % (line, status)
        if hasattr(settings, 'show_priority'):
            line = '%s %-12s' % (line, priority)
        if hasattr(settings, 'show_severity'):
            line = '%s %-12s' % (line, severity)
        line = '%s %-20s' % (line, assignee)
        line = '%s %s' % (line, desc)
        print(line[:settings.columns])

    log_info("%i bug(s) found." % len(buglist))


def prompt_for_bug(settings):
    """ Prompt for the information for a bug
    """
    log_info('Press Ctrl+C at any time to abort.')

    if not hasattr(settings, 'product'):
        product = None
        while not product or len(product) < 1:
            product = input('Enter product: ')
        settings.product = product
    else:
        log_info('Enter product: %s' % settings.product)

    if not hasattr(settings, 'component'):
        component = None
        while not component or len(component) < 1:
            component = input('Enter component: ')
        settings.component = component
    else:
        log_info('Enter component: %s' % settings.component)

    if not hasattr(settings, 'version'):
        line = input('Enter version (default: unspecified): ')
        if len(line):
            settings.version = line
        else:
            settings.version = 'unspecified'
    else:
        log_info('Enter version: %s' % settings.version)

    if not hasattr(settings, 'summary'):
        summary = None
        while not summary or len(summary) < 1:
            summary = input('Enter title: ')
        settings.summary = summary
    else:
        log_info('Enter title: %s' % settings.summary)

    if not hasattr(settings, 'description'):
        line = block_edit('Enter bug description: ')
        if len(line):
            settings.description = line
    else:
        log_info('Enter bug description: %s' % settings.description)

    if not hasattr(settings, 'op_sys'):
        op_sys_msg = 'Enter operating system where this bug occurs: '
        line = input(op_sys_msg)
        if len(line):
            settings.op_sys = line
    else:
        log_info('Enter operating system: %s' % settings.op_sys)

    if not hasattr(settings, 'platform'):
        platform_msg = 'Enter hardware platform where this bug occurs: '
        line = input(platform_msg)
        if len(line):
            settings.platform = line
    else:
        log_info('Enter hardware platform: %s' % settings.platform)

    if not hasattr(settings, 'priority'):
        priority_msg = 'Enter priority (eg. Normal) (optional): '
        line = input(priority_msg)
        if len(line):
            settings.priority = line
    else:
        log_info('Enter priority (optional): %s' % settings.priority)

    if not hasattr(settings, 'severity'):
        severity_msg = 'Enter severity (eg. normal) (optional): '
        line = input(severity_msg)
        if len(line):
            settings.severity = line
    else:
        log_info('Enter severity (optional): %s' % settings.severity)

    if not hasattr(settings, 'alias'):
        alias_msg = 'Enter an alias for this bug (optional): '
        line = input(alias_msg)
        if len(line):
            settings.alias = line
    else:
        log_info('Enter alias (optional): %s' % settings.alias)

    if not hasattr(settings, 'assigned_to'):
        assign_msg = 'Enter assignee (eg. liquidx@gentoo.org) (optional): '
        line = input(assign_msg)
        if len(line):
            settings.assigned_to = line
    else:
        log_info('Enter assignee (optional): %s' % settings.assigned_to)

    if not hasattr(settings, 'cc'):
        cc_msg = 'Enter a CC list (comma separated) (optional): '
        line = input(cc_msg)
        if len(line):
            settings.cc = re.split(r',\s*', line)
    else:
        log_info('Enter a CC list (optional): %s' % settings.cc)

    if not hasattr(settings, 'url'):
        url_msg = 'Enter a URL (optional): '
        line = input(url_msg)
        if len(line):
            settings.url = line
    else:
        log_info('Enter a URL (optional): %s' % settings.url)

    # fixme: groups

    # fixme: status

    # fixme: milestone

    if not hasattr(settings, 'append_command'):
        line = input('Append the output of the'
                     ' following command (leave blank for none): ')
        if len(line):
            settings.append_command = line
    else:
        log_info('Append command (optional): %s' % settings.append_command)


def show_bug_info(bug, settings):
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

    if not hasattr(settings, 'no_attachments'):
        params = {'ids': [bug['id']]}
        bug_attachments = bugtracker.run('Bug.attachments', params)
        bug_attachments = bug_attachments['bugs']['%s' % bug['id']]
        print('%-12s: %d' % ('Attachments', len(bug_attachments)))
        print()
        for attachment in bug_attachments:
            aid = attachment['id']
            desc = attachment['summary']
            when = attachment['creation_time']
            print('[Attachment] [%s] [%s]' % (aid, desc))

    if not hasattr(settings, 'no_comments'):
        params = {'ids': [bug['id']]}
        bug_comments = bugtracker.run('Bug.comments', params)
        bug_comments = bug_comments['bugs']['%s' % bug['id']]['comments']
        print('%-12s: %d' % ('Comments', len(bug_comments)))
        print()
        i = 0
        wrapper = textwrap.TextWrapper(width=settings.columns,
                                       break_long_words=False,
                                       break_on_hyphens=False)
        for comment in bug_comments:
            who = comment['creator']
            when = comment['time']
            what = comment['text']
            print('[Comment #%d] %s : %s' % (i, who, when))
            print('-' * (settings.columns - 1))

            if what is None:
                what = ''

            # print wrapped version
            for line in what.splitlines():
                if len(line) < settings.columns:
                    print(line)
                else:
                    for shortline in wrapper.wrap(line):
                        print(shortline)
            print()
            i += 1


def attach(settings, bugtracker):
    """ Attach a file to a bug given a filename. """
    filename = getattr(settings, 'filename', None)
    content_type = getattr(settings, 'content_type', None)
    bugid = getattr(settings, 'bugid', None)
    summary = getattr(settings, 'summary', None)
    is_patch = getattr(settings, 'is_patch', None)
    comment = getattr(settings, 'comment', None)

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
    login(settings, bugtracker)
    result = bugtracker.run('Bug.add_attachment', params)
    attachid = result['ids'][0]
    log_info('{0} ({1}) has been attached to bug {2}'.format(
        filename, attachid, bugid))


def attachment(settings, bugtracker):
    """ Download or view an attachment given the id."""
    log_info('Getting attachment %s' % settings.attachid)

    params = {}
    params['attachment_ids'] = [settings.attachid]

    if not settings.skip_auth:
        login(settings, bugtracker)

    result = bugtracker.run('Bug.attachments', params)
    result = result['attachments'][settings.attachid]
    view = hasattr(settings, 'view')

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


def get(settings, bugtracker):
    """ Fetch bug details given the bug id """
    if not settings.skip_auth:
        login(settings, bugtracker)

    log_info('Getting bug %s ..' % settings.bugid)
    params = {'ids': [settings.bugid]}
    result = bugtracker.run('Bug.get', params)

    for bug in result['bugs']:
        show_bug_info(bug, settings)


def login(settings, bugtracker):
    """Authenticate a session.
    """
    settings.load_token()
    if settings.bz_token is not None:
        return

    # prompt for username if we were not supplied with it
    if not hasattr(settings, 'user'):
        log_info('No username given.')
        user = input('Username: ')
    else:
        user = settings.user

    # prompt for password if we were not supplied with it
    if not hasattr(settings, 'password'):
        if not hasattr(settings, 'passwordcmd'):
            log_info('No password given.')
            password = getpass.getpass()
        else:
            process = subprocess.Popen(settings.passwordcmd, shell=True,
                                       stdout=subprocess.PIPE)
            password, _ = process.communicate()
            password = password.splitlines()[0]
    else:
        password = settings.password

    # perform login
    params = {}
    params['login'] = user
    params['password'] = password
    log_info('Logging in')
    result = bugtracker.run('User.login', params)
    if 'token' in result:
        settings.save_token(result['token'])


def logout(settings, bugtracker):
    settings.load_token()
    params = {}
    log_info('logging out')
    bugtracker.run('User.logout', params)
    settings.destroy_token()


def modify(settings, bugtracker):
    """Modify an existing bug (eg. adding a comment or changing resolution.)"""
    if hasattr(settings, 'comment_from'):
        try:
            if settings.comment_from == '-':
                settings.comment = sys.stdin.read()
            else:
                settings.comment = open(settings.comment_from, 'r').read()
        except IOError as error:
            raise BugzError('unable to read file: %s: %s' %
                            (settings.comment_from, error))

    if hasattr(settings, 'comment_editor'):
        settings.comment = block_edit('Enter comment:')

    params = {}
    params['ids'] = [settings.bugid]
    if hasattr(settings, 'alias'):
        params['alias'] = settings.alias
    if hasattr(settings, 'assigned_to'):
        params['assigned_to'] = settings.assigned_to
    if hasattr(settings, 'blocks_add'):
        if 'blocks' not in params:
            params['blocks'] = {}
        params['blocks']['add'] = settings.blocks_add
    if hasattr(settings, 'blocks_remove'):
        if 'blocks' not in params:
            params['blocks'] = {}
        params['blocks']['remove'] = settings.blocks_remove
    if hasattr(settings, 'depends_on_add'):
        if 'depends_on' not in params:
            params['depends_on'] = {}
        params['depends_on']['add'] = settings.depends_on_add
    if hasattr(settings, 'depends_on_remove'):
        if 'depends_on' not in params:
            params['depends_on'] = {}
        params['depends_on']['remove'] = settings.depends_on_remove
    if hasattr(settings, 'cc_add'):
        if 'cc' not in params:
            params['cc'] = {}
        params['cc']['add'] = settings.cc_add
    if hasattr(settings, 'cc_remove'):
        if 'cc' not in params:
            params['cc'] = {}
        params['cc']['remove'] = settings.cc_remove
    if hasattr(settings, 'comment'):
        if 'comment' not in params:
            params['comment'] = {}
        params['comment']['body'] = settings.comment
    if hasattr(settings, 'component'):
        params['component'] = settings.component
    if hasattr(settings, 'dupe_of'):
        params['dupe_of'] = settings.dupe_of
    if hasattr(settings, 'groups_add'):
        if 'groups' not in params:
            params['groups'] = {}
        params['groups']['add'] = settings.groups_add
    if hasattr(settings, 'groups_remove'):
        if 'groups' not in params:
            params['groups'] = {}
        params['groups']['remove'] = settings.groups_remove
    if hasattr(settings, 'keywords_set'):
        if 'keywords' not in params:
            params['keywords'] = {}
        params['keywords']['set'] = settings.keywords_set
    if hasattr(settings, 'op_sys'):
        params['op_sys'] = settings.op_sys
    if hasattr(settings, 'platform'):
        params['platform'] = settings.platform
    if hasattr(settings, 'priority'):
        params['priority'] = settings.priority
    if hasattr(settings, 'product'):
        params['product'] = settings.product
    if hasattr(settings, 'resolution'):
        if not hasattr(settings, 'dupe_of'):
            params['resolution'] = settings.resolution
    if hasattr(settings, 'see_also_add'):
        if 'see_also' not in params:
            params['see_also'] = {}
        params['see_also']['add'] = settings.see_also_add
    if hasattr(settings, 'see_also_remove'):
        if 'see_also' not in params:
            params['see_also'] = {}
        params['see_also']['remove'] = settings.see_also_remove
    if hasattr(settings, 'severity'):
        params['severity'] = settings.severity
    if hasattr(settings, 'status'):
        if not hasattr(settings, 'dupe_of'):
            params['status'] = settings.status
    if hasattr(settings, 'summary'):
        params['summary'] = settings.summary
    if hasattr(settings, 'url'):
        params['url'] = settings.url
    if hasattr(settings, 'version'):
        params['version'] = settings.version
    if hasattr(settings, 'whiteboard'):
        params['whiteboard'] = settings.whiteboard

    if hasattr(settings, 'fixed'):
        params['status'] = 'RESOLVED'
        params['resolution'] = 'FIXED'

    if hasattr(settings, 'invalid'):
        params['status'] = 'RESOLVED'
        params['resolution'] = 'INVALID'

    if len(params) < 2:
        raise BugzError('No changes were specified')
    login(settings, bugtracker)
    result = bugtracker.run('Bug.update', params)
    for bug in result['bugs']:
        changes = bug['changes']
        if not len(changes):
            log_info('Added comment to bug %s' % bug['id'])
        else:
            log_info('Modified the following fields in bug %s' % bug['id'])
            for key in changes:
                log_info('%-12s: removed %s' % (key, changes[key]['removed']))
                log_info('%-12s: added %s' % (key, changes[key]['added']))


def post(settings, bugtracker):
    """Post a new bug"""
    login(settings, bugtracker)
    # load description from file if possible
    if hasattr(settings, 'description_from'):
        try:
                if settings.description_from == '-':
                    settings.description = sys.stdin.read()
                else:
                    settings.description = open(settings.description_from, 'r').read()
        except IOError as error:
            raise BugzError('Unable to read from file: %s: %s' %
                            (settings.description_from, error))

    if not hasattr(settings, 'batch'):
        prompt_for_bug(settings)

    # raise an exception if mandatory fields are not specified.
    if not hasattr(settings, 'product'):
        raise RuntimeError('Product not specified')
    if not hasattr(settings, 'component'):
        raise RuntimeError('Component not specified')
    if not hasattr(settings, 'summary'):
        raise RuntimeError('Title not specified')
    if not hasattr(settings, 'description'):
        raise RuntimeError('Description not specified')

    # append the output from append_command to the description
    append_command = getattr(settings, 'append_command', None)
    if append_command is not None and append_command != '':
        append_command_output = subprocess.getoutput(append_command)
        settings.description = settings.description + '\n\n' + \
            '$ ' + append_command + '\n' + \
            append_command_output

    # print submission confirmation
    print('-' * (settings.columns - 1))
    print('%-12s: %s' % ('Product', settings.product))
    print('%-12s: %s' % ('Component', settings.component))
    print('%-12s: %s' % ('Title', settings.summary))
    if hasattr(settings, 'version'):
        print('%-12s: %s' % ('Version', settings.version))
    print('%-12s: %s' % ('Description', settings.description))
    if hasattr(settings, 'op_sys'):
        print('%-12s: %s' % ('Operating System', settings.op_sys))
    if hasattr(settings, 'platform'):
        print('%-12s: %s' % ('Platform', settings.platform))
    if hasattr(settings, 'priority'):
        print('%-12s: %s' % ('Priority', settings.priority))
    if hasattr(settings, 'severity'):
        print('%-12s: %s' % ('Severity', settings.severity))
    if hasattr(settings, 'alias'):
        print('%-12s: %s' % ('Alias', settings.alias))
    if hasattr(settings, 'assigned_to'):
        print('%-12s: %s' % ('Assigned to', settings.assigned_to))
    if hasattr(settings, 'cc'):
        print('%-12s: %s' % ('CC', settings.cc))
    if hasattr(settings, 'url'):
        print('%-12s: %s' % ('URL', settings.url))
    # fixme: groups
    # fixme: status
    # fixme: Milestone
    print('-' * (settings.columns - 1))

    if not hasattr(settings, 'batch'):
        if settings.default_confirm in ['Y', 'y']:
            confirm = input('Confirm bug submission (Y/n)? ')
        else:
            confirm = input('Confirm bug submission (y/N)? ')
        if len(confirm) < 1:
            confirm = settings.default_confirm
        if confirm[0] not in ('y', 'Y'):
            log_info('Submission aborted')
            return

    params = {}
    params['product'] = settings.product
    params['component'] = settings.component
    if hasattr(settings, 'version'):
        params['version'] = settings.version
    params['summary'] = settings.summary
    if hasattr(settings, 'description'):
        params['description'] = settings.description
    if hasattr(settings, 'op_sys'):
        params['op_sys'] = settings.op_sys
    if hasattr(settings, 'platform'):
        params['platform'] = settings.platform
    if hasattr(settings, 'priority'):
        params['priority'] = settings.priority
    if hasattr(settings, 'severity'):
        params['severity'] = settings.severity
    if hasattr(settings, 'alias'):
        params['alias'] = settings.alias
    if hasattr(settings, 'assigned_to'):
        params['assigned_to'] = settings.assigned_to
    if hasattr(settings, 'cc'):
        params['cc'] = settings.cc
    if hasattr(settings, 'url'):
        params['url'] = settings.url

    result = bugtracker.run('Bug.create', params)
    log_info('Bug %d submitted' % result['id'])


def search(settings, bugtracker):
    """Performs a search on the bugzilla database with
the keywords given on the title (or the body if specified).
    """
    valid_keys = ['alias', 'assigned_to', 'component', 'creator',
                  'limit', 'offset', 'op_sys', 'platform',
                  'priority', 'product', 'resolution', 'severity',
                  'version', 'whiteboard']

    params = {}
    d = vars(settings)
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

    if not params:
        raise BugzError('Please give search terms or options.')

    log_info('Searching for bugs meeting the following criteria:')
    for key in params:
        log_info('   {0:<20} = {1}'.format(key, params[key]))

    if not settings.skip_auth:
        login(settings, bugtracker)

    result = bugtracker.run('Bug.search', params)['bugs']

    if not len(result):
        log_info('No bugs found.')
    else:
        list_bugs(result, settings)


def connections(settings, bugtracker):
    print('Known bug trackers:')
    print()
    for tracker in settings.connections:
        print(tracker)


def main():
    ArgParser = make_arg_parser()
    args = ArgParser.parse_args()

    ConfigParser = load_config(getattr(args, 'config_file', None))

    settings = Settings(args, ConfigParser)

    if not hasattr(args, 'func'):
        ArgParser.print_usage()
        return 1

    bugtracker = BugTracker(settings.connection, settings.base)
    try:
        args.func(settings, bugtracker)
    except BugzError as error:
        log_error(error)
        return 1
    except RuntimeError as error:
        log_error(error)
        return 1
    except KeyboardInterrupt:
        log_info('Stopped due to keyboard interrupt')
        return 1

    return 0


if __name__ == "__main__":
    main()
