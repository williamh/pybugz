""" This module is used to communicate with Bugzilla.
"""

import os
import urllib.error
import urllib.parse
import xmlrpc.client

from bugz.exceptions import BugzError
from bugz.log import log_info
from bugz.tokens import Tokens


class BugTracker:
    """ Communicate with the bug tracker.
    """
    def __init__(self, connection, url):
        self.bz_proxy = xmlrpc.client.ServerProxy(url)
        self.bz_token = None
        self.connection = connection
        self.tokens = Tokens()

        parse_result = urllib.parse.urlparse(url)
        new_netloc = parse_result.netloc.split('@')[-1]
        safe_url = parse_result._replace(netloc=new_netloc).geturl()
        log_info("Using [{0}] ({1})".format(connection, safe_url))

        old_token_file = os.path.join(os.environ['HOME'], '.bugz_token')
        try:
            old_token = open(old_token_file).read().strip()
            self.save_token(old_token)
            os.remove(old_token_file)
            print('Your ~/.bugz_token file was moved to ~/.bugz_tokens')
            print('The token was assigned to the {0} connection'
                  .format(self.connection))
            print('If this is not correct, please edit ~/.bugz_tokens')
            print('and adjust the name of the connection.')
            print('This is the name enclosed in square brackets.')
            print('The connections command lists known connections.')
        except (IOError, OSError):
            pass


    def load_token(self):
        """ Load the token for this bugzilla.
        """
        self.bz_token = self.tokens.get_token(self.connection)

    def save_token(self, bz_token):
        """ Save the token for this Bugzilla.
        """
        self.tokens.set_token(self.connection, bz_token)
        self.tokens.save_tokens()

    def destroy_token(self):
        """ Destroy the token for this Bugzilla.
        """
        self.bz_token = None
        self.tokens.remove_token(self.connection)
        self.tokens.save_tokens()

    def run(self, method, params):
        """Attempt to call method with args.
        """
        method = 'self.bz_proxy.'+method
        if self.bz_token is not None:
            params['Bugzilla_token'] = self.bz_token
        try:
            return eval(method)(params)
        except xmlrpc.client.Fault as fault:
            raise BugzError('Bugzilla error: {0}'.format(fault.faultString))
        except xmlrpc.client.ProtocolError as error:
            raise BugzError(error)
        except urllib.error.URLError as error:
            raise BugzError(error)
