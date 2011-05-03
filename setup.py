from bugz import __version__
from distutils.core import setup
from shutil import copy
from os import path

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
)

# copy rc file
script_path = path.dirname(path.abspath(__file__))
rcfile = path.join(script_path,"resources/bugzrc.sample")
if not path.exists(path.expanduser("~/.bugzrc")):
	print "copying "+rcfile+" to ~/.bugzrc"
	copy(rcfile, path.expanduser("~/.bugzrc"))
