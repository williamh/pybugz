# in this file should be unique way to logger feature

LogSettins = {
	'W' : {
		'symb' : '!',
		'word' : 'Warn',
	},
	'E' : {
		'symb' : '#',
		'word' : 'Error',
	},
	'D' : {
		'symb' : '~',
		'word' : 'Dbg',
	},
	'I' : {
		'symb' : '*',
		'word' : 'Info',
	},
	'!' : {
		'symb' : '!',
		'word' : 'UNKNWN',
	},
}

def formatOut(msg, id='!'):
	lines = str(msg).split('\n')
	start = True
	symb=LogSettins[id]['symb']
	word=LogSettins[id]['word'] + ":"

	for line in lines:
		print ' ' + symb + ' ' + line

def log_error(string):
	formatOut(string, 'E')
	return

def log_warn(string):
	formatOut(string, 'W')
	return

def log_info(string):
	formatOut(string, 'I')
	return

def log_debug(string, verboseness=0):
	formatOut(string, 'D')
	return
