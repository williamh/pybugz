import argparse

import bugz.cli

from bugz import __version__


def make_arg_parser():
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument('--config-file',
                        help='read an alternate configuration file')
    parser.add_argument('--connection',
                        help='use [connection] section of your '
                        'configuration file')
    parser.add_argument('-b', '--base',
                        help='base URL of Bugzilla')
    parser.add_argument('-u', '--user',
                        help='username')
    parser.add_argument('-p', '--password',
                        help='password')
    parser.add_argument('--passwordcmd',
                        help='command to evaluate for the password')
    parser.add_argument('-k', '--key',
                        help='API key')
    parser.add_argument('-q', '--quiet',
                        action='store_true',
                        help='quiet mode')
    parser.add_argument('-d', '--debug',
                        type=int,
                        help='debug level (from 0 to 3)')
    parser.add_argument('--columns',
                        type=int,
                        help='maximum number of columns output should use')
    parser.add_argument('--encoding',
                        help='output encoding (default: utf-8) (deprecated)')
    parser.add_argument('--skip-auth',
                        action='store_true',
                        help='skip Authentication.')
    parser.add_argument('--version',
                        action='version',
                        help='show program version and exit',
                        version='%(prog)s ' + __version__)

    subparsers = parser.add_subparsers(title='sub-commands',
                                       description='use -h after '
                                       'a sub-command for more help')

    attach_parser = subparsers.add_parser('attach',
                                          argument_default=argparse.SUPPRESS,
                                          help='attach file to a bug')
    attach_parser.add_argument('bugid',
                               help='the ID of the bug where the file '
                               'should be attached')
    attach_parser.add_argument('filename',
                               help='the name of the file to attach')
    attach_parser.add_argument('-c', '--content-type',
                               help='mimetype of the file e.g. '
                               'text/plain (default: auto-detect)')
    attach_parser.add_argument('-d', '--description',
                               dest='comment',
                               help='a long description of the attachment')
    attach_parser.add_argument('-p', '--patch',
                               action='store_true',
                               dest='is_patch',
                               help='attachment is a patch')
    attach_parser.add_argument('-t', '--title',
                               dest='summary',
                               help='a short description of the '
                               'attachment (default: filename).')
    attach_parser.set_defaults(func=bugz.cli.attach)

    attachment_parser = subparsers.add_parser('attachment',
                                              argument_default=argparse.SUPPRESS,
                                              help='get an attachment '
                                              'from Bugzilla')
    attachment_parser.add_argument('attachid',
                                   help='the ID of the attachment')
    attachment_parser.add_argument('-v', '--view',
                                   action="store_true",
                                   help='print attachment rather than save')
    attachment_parser.set_defaults(func=bugz.cli.attachment)

    connections_parser = subparsers.add_parser('connections',
                                               help='list known bug trackers')
    connections_parser.set_defaults(func=bugz.cli.connections)

    get_parser = subparsers.add_parser('get',
                                       argument_default=argparse.SUPPRESS,
                                       help='get a bug from bugzilla')
    get_parser.add_argument('bugid',
                            help='the ID of the bug to retrieve')
    get_parser.add_argument("-a", "--no-attachments",
                            action="store_true",
                            help='do not show attachments')
    get_parser.add_argument("-n", "--no-comments",
                            action="store_true",
                            help='do not show comments')
    get_parser.set_defaults(func=bugz.cli.get)

    modify_parser = subparsers.add_parser('modify',
                                          argument_default=argparse.SUPPRESS,
                                          help='modify a bug '
                                          '(eg. post a comment)')
    modify_parser.add_argument('bugid',
                               help='the ID of the bug to modify')
    modify_parser.add_argument('--alias',
                               help='change the alias for this bug')
    modify_parser.add_argument('-a', '--assigned-to',
                               help='change assignee for this bug')
    modify_parser.add_argument('--add-blocked',
                               action='append',
                               dest='blocks_add',
                               help='add a bug to the blocked list')
    modify_parser.add_argument('--remove-blocked',
                               action='append',
                               dest='blocks_remove',
                               help='remove a bug from the blocked list')
    modify_parser.add_argument('--add-dependson',
                               action='append',
                               dest='depends_on_add',
                               help='add a bug to the depends list')
    modify_parser.add_argument('--remove-dependson',
                               action='append',
                               dest='depends_on_remove',
                               help='remove a bug from the depends list')
    modify_parser.add_argument('--add-cc',
                               action='append',
                               dest='cc_add',
                               help='add an email to the CC list')
    modify_parser.add_argument('--remove-cc',
                               action='append',
                               dest='cc_remove',
                               help='remove an email from the CC list')
    modify_parser.add_argument('-c', '--comment',
                               help='add comment from command line')
    modify_parser.add_argument('-C', '--comment-editor',
                               action='store_true',
                               help='add comment via default editor')
    modify_parser.add_argument('-F', '--comment-from',
                               help='add comment from file.  If -C is '
                               'also specified, the editor will be opened '
                               'with this file as its contents.')
    modify_parser.add_argument('--component',
                               help='change the component for this bug')
    modify_parser.add_argument('-d', '--duplicate',
                               dest='dupe_of',
                               type=int,
                               help='this bug is a duplicate')
    modify_parser.add_argument('--add-group',
                               action='append',
                               dest='groups_add',
                               help='add a group to this bug')
    modify_parser.add_argument('--remove-group',
                               action='append',
                               dest='groups_remove',
                               help='remove agroup from this bug')
    modify_parser.add_argument('--set-keywords',
                               action='append',
                               dest='keywords_set',
                               help='set bug keywords')
    modify_parser.add_argument('--op-sys',
                               help='change the operating system for this bug')
    modify_parser.add_argument('--platform',
                               help='change the hardware platform '
                               'for this bug')
    modify_parser.add_argument('--priority',
                               help='change the priority for this bug')
    modify_parser.add_argument('--product',
                               help='change the product for this bug')
    modify_parser.add_argument('-r', '--resolution',
                               help='set new resolution '
                               '(if status = RESOLVED)')
    modify_parser.add_argument('--add-see-also',
                               action='append',
                               dest='see_also_add',
                               help='add a "see also" URL to this bug')
    modify_parser.add_argument('--remove-see-also',
                               action='append',
                               dest='see_also_remove',
                               help='remove a"see also" URL from this bug')
    modify_parser.add_argument('-S', '--severity',
                               help='set severity for this bug')
    modify_parser.add_argument('-s', '--status',
                               help='set new status of bug (eg. RESOLVED)')
    modify_parser.add_argument('-t', '--title',
                               dest='summary',
                               help='set title of bug')
    modify_parser.add_argument('-u', '--unassign',
                               dest='unassign', action='store_true',
                               help='Reassign the bug to default owner')
    modify_parser.add_argument('-U', '--url',
                               help='set URL field of bug')
    modify_parser.add_argument('-v', '--version',
                               help='set the version for this bug'),
    modify_parser.add_argument('-w', '--whiteboard',
                               help='set Status whiteboard'),
    modify_parser.add_argument('--fixed',
                               action='store_true',
                               help='mark bug as RESOLVED, FIXED')
    modify_parser.add_argument('--invalid',
                               action='store_true',
                               help='mark bug as RESOLVED, INVALID')
    modify_parser.set_defaults(func=bugz.cli.modify)

    post_parser = subparsers.add_parser('post',
                                        argument_default=argparse.SUPPRESS,
                                        help='post a new bug into bugzilla')
    post_parser.add_argument('--product',
                             help='product')
    post_parser.add_argument('--component',
                             help='component')
    post_parser.add_argument('--version',
                             help='version of the product')
    post_parser.add_argument('-t', '--title',
                             dest='summary',
                             help='title of bug')
    post_parser.add_argument('-d', '--description',
                             help='description of the bug')
    post_parser.add_argument('--op-sys',
                             help='set the operating system')
    post_parser.add_argument('--platform',
                             help='set the hardware platform')
    post_parser.add_argument('--priority',
                             help='set priority for the new bug')
    post_parser.add_argument('-S', '--severity',
                             help='set the severity for the new bug')
    post_parser.add_argument('--alias',
                             help='set the alias for this bug')
    post_parser.add_argument('-a', '--assigned-to',
                             help='assign the bug to someone')
    post_parser.add_argument('--cc',
                             help='add a list of emails to CC list')
    post_parser.add_argument('-U', '--url',
                             help='set URL field of bug')
    post_parser.add_argument('-F', '--description-from',
                             help='load description from file')
    post_parser.add_argument('--append-command',
                             help='append output from command to description')
    post_parser.add_argument('--batch',
                             action="store_true",
                             help='do not prompt for any values')
    post_parser.add_argument('--default-confirm',
                             choices=['y', 'Y', 'n', 'N'],
                             default='y',
                             help='default answer to confirmation question')
    post_parser.set_defaults(func=bugz.cli.post)

    products_parser = subparsers.add_parser('products',
        argument_default=argparse.SUPPRESS, help='list available products')
    products_parser.set_defaults(func=bugz.cli.products)
    products_parser.add_argument(
        '--json',
        action='store_true',
        help='format results as newline separated json records',
        default=False)
    products_parser.add_argument(
        '--format',
        type=str,
        help='custom format. Format: {product[field]} (see --json)',
        default=None)

    components_parser = subparsers.add_parser('components',
        argument_default=argparse.SUPPRESS, help='list available components')
    components_parser.set_defaults(func=bugz.cli.components)
    components_parser.add_argument(
        '--json',
        action='store_true',
        help='format results as newline separated json records',
        default=False)
    components_parser.add_argument(
        '--format',
        type=str,
        help='custom format. Format: {product[field]} (see --json)',
        default=None)

    search_parser = subparsers.add_parser('search',
                                          argument_default=argparse.SUPPRESS,
                                          help='search for bugs in bugzilla')
    search_parser.add_argument('terms',
                               nargs='*',
                               help='strings to search for in '
                               'the title and/or body')
    search_parser.add_argument('--alias',
                               help='The unique alias for this bug')
    search_parser.add_argument('-a', '--assigned-to',
                               help='email the bug is assigned to')
    search_parser.add_argument('-C', '--component',
                               action='append',
                               help='restrict by component (1 or more)')
    search_parser.add_argument('-r', '--creator',
                               help='email of the person who created the bug')
    search_parser.add_argument('-l', '--limit',
                               type=int,
                               help='Limit the number of records '
                               'returned by a search')
    search_parser.add_argument('--offset',
                               type=int,
                               help='Set the start position for a search')
    search_parser.add_argument('--op-sys',
                               action='append',
                               help='restrict by Operating System '
                               '(one or more)')
    search_parser.add_argument('--platform',
                               action='append',
                               help='restrict by platform (one or more)')
    search_parser.add_argument('--priority',
                               action='append',
                               help='restrict by priority (one or more)')
    search_parser.add_argument('--product',
                               action='append',
                               help='restrict by product (one or more)')
    search_parser.add_argument('--resolution',
                               help='restrict by resolution')
    search_parser.add_argument('--severity',
                               action='append',
                               help='restrict by severity (one or more)')
    search_parser.add_argument('-s', '--status',
                               action='append',
                               help='restrict by status '
                               '(one or more, use all for all statuses)')
    search_parser.add_argument('-S', '--not-status',
                               action='append',
                               help='exclude by status '
                               '(one or more, use all for all statuses)')
    search_parser.add_argument('-v', '--version',
                               action='append',
                               help='restrict by version (one or more)')
    search_parser.add_argument('-w', '--whiteboard',
                               help='status whiteboard')
    search_parser.add_argument('--show-status',
                               action='store_true',
                               help='show status of bugs')
    search_parser.add_argument('--show-priority',
                               action='store_true',
                               help='show priority of bugs')
    search_parser.add_argument('--show-severity',
                               action='store_true',
                               help='show severity of bugs')
    search_parser.add_argument(
        '--format',
        type=str,
        help='custom format found bugs. Format: {bug[field]} (see --json)',
        default=None)
    search_parser.add_argument(
        '--json',
        action='store_true',
        help='format results as newline separated json records',
        default=False)

    search_parser.set_defaults(func=bugz.cli.search)

    return parser
