import mimetypes
import os
import re
import sys
import shutil
import tempfile

BUGZ_COMMENT_TEMPLATE = """
BUGZ: ---------------------------------------------------
%s
BUGZ: Any line beginning with 'BUGZ:' will be ignored.
BUGZ: ---------------------------------------------------
"""

DEFAULT_NUM_COLS = 80

#
# Auxiliary functions
#


def get_content_type(filename):
    # Keep in sync with Lib/mimetypes.py
    encoding_map = {
        'bzip2': 'application/x-bzip2',
        'compress': 'application/x-compress',
        'gzip': 'application/gzip',
        'xz': 'application/x-xz',
    }
    # Last addition was brotli, rest have been since 3.4
    if sys.version_info >= (3, 9):
        encoding_map['br'] = 'application/x-brotli'

    mimetype, encoding = mimetypes.guess_type(filename) or ('application/octet-stream', None)

    # guess_type returns encoding of the file separately from the encoded file. Leading .txt.gz having
    # the mime of text/plain, this isn't desirable so return the mimetype of the encoding
    # https://github.com/williamh/pybugz/issues/113
    return mimetype if encoding is None else encoding_map[encoding]

def raw_input_block():
    """ Allows multiple line input until a Ctrl+D is detected.

    @rtype: string
    """
    target = ''
    while True:
        try:
            line = input()
            target += line + '\n'
        except EOFError:
            return target

#
# This function was lifted from Bazaar 1.9.
#


def terminal_width():
    """Return estimated terminal width."""
    return shutil.get_terminal_size().columns


def launch_editor(initial_text, comment_from='', comment_prefix='BUGZ:'):
    """Launch an editor with some default text.

    Lifted from Mercurial 0.9.
    @rtype: string
    """
    (fd, name) = tempfile.mkstemp("bugz")
    with os.fdopen(fd, "w") as f:
        f.write(comment_from)
        f.write(initial_text)

    editor = (os.environ.get("BUGZ_EDITOR") or os.environ.get("EDITOR"))
    if editor:
        result = os.system("%s \"%s\"" % (editor, name))
        if result != 0:
            raise RuntimeError('Unable to launch editor: %s' % editor)

        with open(name) as f:
            new_text = f.read()
        new_text = re.sub('(?m)^%s.*\n' % comment_prefix, '', new_text)
        os.unlink(name)
        return new_text

    return ''


def block_edit(comment, comment_from=''):
    editor = (os.environ.get('BUGZ_EDITOR') or os.environ.get('EDITOR'))

    if not editor:
        print(comment + ': (Press Ctrl+D to end)')
        new_text = raw_input_block()
        return new_text

    initial_text = '\n'.join(['BUGZ: %s' % line
                              for line in comment.splitlines()])
    new_text = launch_editor(BUGZ_COMMENT_TEMPLATE % initial_text,
                             comment_from)

    if new_text.strip():
        return new_text
    else:
        return ''
