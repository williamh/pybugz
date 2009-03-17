from distutils.core import setup

setup(
    name = 'pybugz',
    version = '0.7.4',
    author = 'Alastair Tse',
    author_email = 'alastair@liquidx.net',
    url = 'http://www.github.com/ColdWind/pybugz',
    description = 'python interface to bugzilla',
    packages = ['bugz'],
    scripts = ['bin/bugz']
)
