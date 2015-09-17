import glob
from setuptools import setup

from bugz import __version__

setup(
	name='pybugz',
	version=__version__,
	description='python interface to bugzilla',
	long_description='python interface to bugzilla',
	author='Alastair Tse',
	author_email='alastair@liquidx.net',
	license="GPL-2",
	url='http://www.liquidx.net/pybugz',
	packages=['bugz'],
	platforms=['any'],
	data_files=[
		('share/man/man1', ['man/bugz.1']),
		('share/man/man5', ['man/pybugz.d.5']),
		('share/pybugz.d', glob.glob('pybugz.d/*.conf')),
	],
	entry_points={'console_scripts': ['bugz=bugz.main:main']},
)
