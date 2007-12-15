# Copyright 1999-2006 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: /var/cvsroot/gentoo-x86/dev-python/feedparser/feedparser-4.1.ebuild,v 1.6 2006/07/16 13:58:13 liquidx Exp $

inherit distutils

DESCRIPTION="Command line interface to (Gentoo) Bugzilla"
HOMEPAGE="http://svn.liquidx.net/svn/python/pybugz/README"
SRC_URI="http://media.liquidx.net/static/pybugz/${P}.tar.gz"
LICENSE="GPL-2"
SLOT="0"
KEYWORDS="x86"
IUSE=""
DEPEND=">=dev-lang/python-2.4
	dev-python/elementtree"

