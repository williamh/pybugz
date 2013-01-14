#This module contains a set of common routines for logging messages.

LogSettings = {
	'W' : {
		'sym' : '!',
		'word' : 'Warn',
	},
	'E' : {
		'sym' : '#',
		'word' : 'Error',
	},
	'D' : {
		'sym' : '~',
		'word' : 'Dbg',
	},
	'!' : {
		'sym' : '!',
		'word' : 'UNKNWN',
	},
}

def formatOut(msg, id='!'):
	lines = str(msg).split('\n')
	start = True
	sym=LogSettings[id]['sym']
	word=LogSettings[id]['word'] + ":"

	for line in lines:
		print ' ' + sym + ' ' + line

def log_error(string):
	formatOut(string, 'E')
	return

def log_warn(string):
	formatOut(string, 'W')
	return

def log_info(string):
	formatOut(string, 'I')
	return

def log_debug(string):
	formatOut(string, 'D')
	return
