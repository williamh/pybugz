# TODO: use the python's  'logging' feature?

dbglvl = 0
quiet = False

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

def setQuiet(newQuiet):
	global quiet
	quiet = newQuiet

def setDebugLvl(newlvl):
	global dbglvl
	if not newlvl:
		return
	if newlvl > 3:
		log_warn("bad debug level '{0}', using '3'".format(str(newlvl)))
		dbglvl = 3
	else:
		dbglvl = newlvl

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
	global quiet
	global dbglvl
	# debug implies info
	if not quiet or dbglvl:
		formatOut(string, 'I')
	return

def log_debug(string, verboseness=1):
	global dbglvl
	if dbglvl >= verboseness:
		formatOut(string, 'D')
	return
