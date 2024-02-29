""" This module contains a set of routines for logging messages.

    If someone wants to convert this to use python's built-in logging,
    patches are welcome.
"""

debugLevel = 0
quiet = False

LogSettings = {
    'W': {
        'sym': '!',
        'word': 'Warn',
    },
    'E': {
        'sym': '#',
        'word': 'Error',
    },
    'D': {
        'sym': '~',
        'word': 'Dbg',
    },
    'I': {
        'sym': '*',
        'word': 'Info',
    },
    '!': {
        'sym': '!',
        'word': 'UNKNWN',
    },
}


def log_setQuiet(newQuiet):
    global quiet
    quiet = newQuiet


def log_setDebugLevel(newLevel):
    global debugLevel
    if not newLevel:
        return
    if newLevel > 3:
        log_warn("bad debug level '{0}', using '3'".format(str(newLevel)))
        debugLevel = 3
    else:
        debugLevel = newLevel


def formatOut(msg, id='!'):
    lines = str(msg).split('\n')
    sym = LogSettings[id]['sym']
    word = LogSettings[id]['word'] + ":"

    for line in lines:
        print(' {0} {1} {2}'.format(sym, word, line))


def log_error(string):
    formatOut(string, 'E')


def log_warn(string):
    formatOut(string, 'W')


def log_info(string):
    # debug implies info
    if not quiet or debugLevel:
        formatOut(string, 'I')


def log_debug(string, msgLevel=1):
    if debugLevel >= msgLevel:
        formatOut(string, 'D')
