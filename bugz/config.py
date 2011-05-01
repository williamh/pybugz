#!/usr/bin/env python

from bugz import __version__
import csv
import locale

BUGZ_USER_AGENT = 'PyBugz/%s +http://www.github.com/williamh/pybugz/' % __version__

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

		# TODO: Add -s option (status) as cmdline arg instead of the hardcoded
		# one. Bugzilla will set the status itself if not given
		'post': {
		'product': '',
		'version': 'unspecified',
		'rep_platform': 'All',
		'op_sys': 'Linux',
		'priority': 'P2',
		'bug_severity': 'normal',
		'assigned_to': '',
		'keywords': '',
		'dependson':'',
		'blocked':'',
		'component': '',
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
		'ispatch': '',
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
		# NEW, ASSIGNED and REOPENED is obsolete as of bugzilla 3.x and has
		# been removed from bugs.gentoo.org on 2011/05/01
		'bug_status': ['NEW', 'ASSIGNED', 'REOPENED', 'UNCONFIRMED', 'CONFIRMED', 'IN_PROGRESS'],
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
		},

		'namedcmd': {
		'cmdtype' : 'runnamed',
		'namedcmd' : '',
		'ctype':'csv'
		}
	}

	choices = {
		'status': {
		'unconfirmed': 'UNCONFIRMED',
		'confirmed': 'CONFIRMED',
		'new': 'NEW',
		'assigned': 'ASSIGNED',
		'in_progress': 'IN_PROGRESS',
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
		'wontfix': 'WONTFIX',
		'lated': 'LATER',
		'remind': 'REMIND',
		'worksforme': 'WORKSFORME',
		'cantfix': 'CANTFIX',
		'needinfo': 'NEEDINFO',
		'test-request': 'TEST-REQUEST',
		'upstream': 'UPSTREAM',
		'duplicate': 'DUPLICATE',
		},

		'severity': [
		'blocker',
		'critical',
		'major',
		'normal',
		'minor',
		'trivial',
		'enhancement',
		'QA',
		],

		'priority': {
		1:'P1',
		2:'P2',
		3:'P3',
		4:'P4',
		5:'P5',
		}

	}

#
# Global configuration
#

try:
	config
except NameError:
	config = BugzConfig()

