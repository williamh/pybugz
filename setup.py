import os
from distutils.core import setup
from bugz import __version__

# when using virtualenv; trust that man will find the nearby directory
if 'VIRTUAL_ENV' in os.environ:
	man_pages = 'man/man1'
else:
	man_pages = '/usr/share/man/man1'

setup(
	name = 'pybugz',
	version = __version__,
	description = 'python interface to bugzilla',
	author = 'Alastair Tse',
	author_email = 'alastair@liquidx.net',
	url = 'http://www.liquidx.net/pybugz',
	license = "GPL-2",
	platforms = ['any'],
	packages = ['bugz'],
	scripts = ['bin/bugz'],
	data_files = [
		(man_pages, ['man/bugz.1']),
	],
)
