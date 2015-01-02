import bugz.cli

from bugz import __version__


def make_attach_parser(subparsers):
	attach_parser = subparsers.add_parser('attach',
		help='attach file to a bug')
	attach_parser.add_argument('bugid',
		help='the ID of the bug where the file should be attached')
	attach_parser.add_argument('filename',
		help='the name of the file to attach')
	attach_parser.add_argument('-c', '--content-type',
		help='mimetype of the file e.g. text/plain (default: auto-detect)')
	attach_parser.add_argument('-d', '--description',
		help='a long description of the attachment',
		dest='comment')
	attach_parser.add_argument('-p', '--patch',
		action='store_true',
		help='attachment is a patch',
		dest='is_patch')
	attach_parser.add_argument('-t', '--title',
		help='a short description of the attachment (default: filename).',
		dest='summary')
	attach_parser.set_defaults(func=bugz.cli.attach)


def make_attachment_parser(subparsers):
	attachment_parser = subparsers.add_parser('attachment',
		help='get an attachment from bugzilla')
	attachment_parser.add_argument('attachid',
		help='the ID of the attachment')
	attachment_parser.add_argument('-v', '--view',
		action="store_true",
		help='print attachment rather than save')
	attachment_parser.set_defaults(func=bugz.cli.attachment)


def make_get_parser(subparsers):
	get_parser = subparsers.add_parser('get',
		help='get a bug from bugzilla')
	get_parser.add_argument('bugid',
		help='the ID of the bug to retrieve.')
	get_parser.add_argument("-a", "--no-attachments",
		action="store_true",
		help='do not show attachments')
	get_parser.add_argument("-n", "--no-comments",
		action="store_true",
		help='do not show comments')
	get_parser.set_defaults(func=bugz.cli.get)


def make_login_parser(subparsers):
	login_parser = subparsers.add_parser('login',
		help='log into bugzilla')
	login_parser.set_defaults(func=bugz.cli.login)


def make_logout_parser(subparsers):
	logout_parser = subparsers.add_parser('logout',
		help='log out of bugzilla')
	logout_parser.set_defaults(func=bugz.cli.logout)


def make_modify_parser(subparsers):
	modify_parser = subparsers.add_parser('modify',
		help='modify a bug (eg. post a comment)')
	modify_parser.add_argument('bugid',
		help='the ID of the bug to modify')
	modify_parser.add_argument('--alias',
		help='change the alias for this bug')
	modify_parser.add_argument('-a', '--assigned-to',
		help='change assignee for this bug')
	modify_parser.add_argument('--add-blocked',
		action='append',
		help='add a bug to the blocked list',
		dest='blocks_add')
	modify_parser.add_argument('--remove-blocked',
		action='append',
		help='remove a bug from the blocked list',
		dest='blocks_remove')
	modify_parser.add_argument('--add-dependson',
		action='append',
		help='add a bug to the depends list',
		dest='depends_on_add')
	modify_parser.add_argument('--remove-dependson',
		action='append',
		help='remove a bug from the depends list',
		dest='depends_on_remove')
	modify_parser.add_argument('--add-cc',
		action='append',
		help='add an email to the CC list',
		dest='cc_add')
	modify_parser.add_argument('--remove-cc',
		action='append',
		help='remove an email from the CC list',
		dest='cc_remove')
	modify_parser.add_argument('-c', '--comment',
		help='add comment from command line')
	modify_parser.add_argument('-C', '--comment-editor',
		action='store_true',
		help='add comment via default editor')
	modify_parser.add_argument('-F', '--comment-from',
		help='add comment from file.  If -C is also specified,'
		' the editor will be opened with this file'
		' as its contents.')
	modify_parser.add_argument('--component',
		help='change the component for this bug')
	modify_parser.add_argument('-d', '--duplicate',
		type=int,
		help='this bug is a duplicate',
		dest='dupe_of')
	modify_parser.add_argument('--add-group',
		action='append',
		help='add a group to this bug',
		dest='groups_add')
	modify_parser.add_argument('--remove-group',
		action='append',
		help='remove agroup from this bug',
		dest='groups_remove')
	modify_parser.add_argument('--set-keywords',
		action='append',
		help='set bug keywords',
		dest='keywords_set')
	modify_parser.add_argument('--op-sys',
		help='change the operating system for this bug')
	modify_parser.add_argument('--platform',
		help='change the hardware platform for this bug')
	modify_parser.add_argument('--priority',
		help='change the priority for this bug')
	modify_parser.add_argument('--product',
		help='change the product for this bug')
	modify_parser.add_argument('-r', '--resolution',
		help='set new resolution (only if status = RESOLVED)')
	modify_parser.add_argument('--add-see-also',
		action='append',
		help='add a "see also" URL to this bug',
		dest='see_also_add')
	modify_parser.add_argument('--remove-see-also',
		action='append',
		help='remove a"see also" URL from this bug',
		dest='see_also_remove')
	modify_parser.add_argument('-S', '--severity',
		help='set severity for this bug')
	modify_parser.add_argument('-s', '--status',
		help='set new status of bug (eg. RESOLVED)')
	modify_parser.add_argument('-t', '--title',
		help='set title of bug',
		dest='summary')
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


def make_post_parser(subparsers):
	post_parser = subparsers.add_parser('post',
		help='post a new bug into bugzilla')
	post_parser.add_argument('--product',
		help='product')
	post_parser.add_argument('--component',
		help='component')
	post_parser.add_argument('--version',
		help='version of the product')
	post_parser.add_argument('-t', '--title',
		help='title of bug',
		dest='summary')
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
		help='assign bug to someone other than the default assignee')
	post_parser.add_argument('--cc',
		help='add a list of emails to CC list')
	post_parser.add_argument('-U', '--url',
		help='set URL field of bug')
	post_parser.add_argument('-F', '--description-from',
		help='description from contents of file')
	post_parser.add_argument('--append-command',
		help='append the output of a command to the description')
	post_parser.add_argument('--batch',
		action="store_true",
		help='do not prompt for any values')
	post_parser.add_argument('--default-confirm',
		choices=['y', 'Y', 'n', 'N'],
		default='y',
		help='default answer to confirmation question')
	post_parser.set_defaults(func=bugz.cli.post)


def make_search_parser(subparsers):
	search_parser = subparsers.add_parser('search',
		help='search for bugs in bugzilla')
	search_parser.add_argument('terms',
		nargs='*',
		help='strings to search for in title and/or body')
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
		help='Limit the number of records returned in a search')
	search_parser.add_argument('--offset',
		type=int,
		help='Set the start position for a search')
	search_parser.add_argument('--op-sys',
		action='append',
		help='restrict by Operating System (one or more)')
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
		help='restrict by status (one or more, use all for all statuses)')
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
	search_parser.set_defaults(func=bugz.cli.search)


def make_connections_parser(subparsers):
	connections_parser = subparsers.add_parser('connections',
		help='list known bug trackers')
	connections_parser.set_defaults(func=bugz.cli.connections)


def make_parser(parser):
	parser.add_argument('--config-file',
		help='read an alternate configuration file')
	parser.add_argument('--connection',
		help='use [connection] section of your configuration file')
	parser.add_argument('-b', '--base',
		help='base URL of Bugzilla')
	parser.add_argument('-u', '--user',
		help='username for commands requiring authentication')
	parser.add_argument('-p', '--password',
		help='password for commands requiring authentication')
	parser.add_argument('--passwordcmd',
		help='password command to evaluate for commands requiring authentication')
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
	subparsers = parser.add_subparsers(help='help for sub-commands')
	make_attach_parser(subparsers)
	make_attachment_parser(subparsers)
	make_get_parser(subparsers)
	make_login_parser(subparsers)
	make_logout_parser(subparsers)
	make_modify_parser(subparsers)
	make_post_parser(subparsers)
	make_search_parser(subparsers)
	make_connections_parser(subparsers)
	return parser
