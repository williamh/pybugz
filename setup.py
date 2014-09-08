import glob
import os
from distutils.core import setup
from bugz import __version__

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
		('share/man/man1', ['man/bugz.1']),
		('share/man/man5', ['man/pybugz.d.5']),
		('share/pybugz.d', glob.glob('pybugz.d/*.conf')),
	],
)
