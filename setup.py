from bugz import __version__
from distutils.core import setup
try:
	from distutils.command.build_py import build_py_2to3 as build_py
	from distutils.command.build_scripts import build_scripts_2to3 as build_scripts
except ImportError:
	from distutils.command.build_py import build_py
	from distutils.command.build_scripts import build_scripts

# when using virtualenv; trust that man will find the nearby directory
import os
man_pages = '/usr/share/man/man1'
if 'VIRTUAL_ENV' in os.environ:
	# if relative, then interpreted as relative to installation prefix
	man_pages = 'man/man1'

setup(
	name = 'pybugz',
	version = __version__,
	description = 'python interface to bugzilla',
	author = 'Alastair Tse',
	author_email = 'alastair@liquidx.net',
	url = 'http://www.liquidx.net/pybuggz',
	license = "GPL-2",
	platforms = ['any'],
	packages = ['bugz'],
	scripts = ['bin/bugz'],
	data_files = [
		(man_pages, ['man/bugz.1']),
	],
	cmdclass = {'build_py': build_py, 'build_scripts': build_scripts},
)
