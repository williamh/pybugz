PyBugz - Python Bugzilla Interface
----------------------------------

Bugzilla has a very inefficient user interface, so I've written a
command line utility to interact with it. This is mainly done to help
me with closing bugs on Gentoo Bugzilla by grabbing patches, ebuilds
and so on.

Author
------
Alastair Tse <alastair@liquidx.net>. Copyright (c) 2006 under GPL-2.

Requirements
------------

* Python 3.3 or later

Features
--------

* Searching bugzilla
* Listing details of a bug including comments and attachments
* Downloading/viewing attachments from bugzilla
* Posting bugs, comments, and making changes to an existing bug.
* Adding attachments to a bug.

Usage/Workflow
--------------

PyBugz comes with a command line interface called "bugz". It's
operation is similar in style to cvs/svn where a subcommand is
required for operation. 

To explain how it works, I will use a typical workflow for Gentoo
development. 

1) Searching bugzilla for bugs I can fix, I'll run the command:
---------------------------------------------------------------

$ bugz search "version bump" --assigned-to liquidx@gentoo.org

 * Using https://bugs.gentoo.org/xmlrpc.cgi
 * Searching for "version bump"
 101968 liquidx              net-im/msnlib version bump
 125468 liquidx              version bump for dev-libs/g-wrap-1.9.6
 130608 liquidx              app-dicts/stardict version bump: 2.4.7

2) Narrow down on bug #101968, I can execute:
---------------------------------------------

$ bugz get 101968

 * Using https://bugs.gentoo.org/xmlrpc.cgi
 * Getting bug 130608 ..
Title       : app-dicts/stardict version bump: 2.4.7
Assignee    : liquidx@gentoo.org
Reported    : 2006-04-20 07:36 PST
Updated     : 2006-05-29 23:18:12 PST
Status      : NEW
URL         : http://stardict.sf.net
Severity    : enhancement
Reporter    : dushistov@mail.ru
Priority    : P2
Comments    : 3
Attachments : 1

[ATTACH] [87844] [stardict 2.4.7 ebuild]

[Comment #1] dushistov@----.ru : 2006-04-20 07:36 PST
...

3) Now this bug has an attachment submitted by the user, so I can
   easily pull that attachment in:
-----------------------------------------------------------------

$ bugz attachment 87844

 * Using https://bugs.gentoo.org/xmlrpc.cgi
 * Getting attachment 87844
 * Saving attachment: "stardict-2.4.7.ebuild"

4) If the ebuild is suitable, we can commit it using our normal
   repoman tools, and close the bug.
---------------------------------------------------------------

$ bugz modify 130608 --fixed -c "Thanks for the ebuild. Committed to
  portage" 

or if we find that the bug is invalid, we can close it by using:

$ bugz modify 130608 --invalid -c "Not reproducable"

Other options
-------------

bugz has an extensive help system for commands and options.

bugz --help gives help for the global options and subcommands, and
bugz <subcommand> --help gives help for that specific subcommand.

PyBugz Configuration
--------------------

PyBugz supports a configuration system which defines defaults for
multiple Bugzilla installations and allows the system administrator and
individual users to override or add to these settings.

The supplied defaults are stored in /usr/share/pybugz.d/*.conf. The
system administrator can override or add to these defaults on a site-wide
basis by creating a directory /etc/pybugz.d and adding files with a
.conf extension to this directory. Individual users can override or add
to all of these settings by placing a file named .bugzrc in their home
directory.

For more information about this configuration system, see the
pybugz.d (5) man page.
