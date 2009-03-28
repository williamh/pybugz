from distutils.core import setup

setup(
    name = 'pybugz',
    version = '0.7.4_rc1',
    description = 'python interface to bugzilla',
    author = 'Alastair Tse',
    author_email = 'alastair@liquidx.net',
    url = 'http://www.liquidx.net/pybuggz',
    license = "GPL-2",
    platforms = ['any'],
    packages = ['bugz'],
    scripts = ['bin/bugz']
)
