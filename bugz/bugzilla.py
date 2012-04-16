# Author: Mike Gilbert <floppym@gentoo.org>
# This code is released into the public domain.
# As of this writing, the Bugzilla web service is documented at the
# following URL:
# http://www.bugzilla.org/docs/4.2/en/html/api/Bugzilla/WebService.html

from cookielib import CookieJar
from urllib import splittype, splithost, splituser, splitpasswd
from urllib2 import build_opener, HTTPBasicAuthHandler, HTTPCookieProcessor
from urllib2 import HTTPPasswordMgrWithDefaultRealm, Request
from xmlrpclib import ProtocolError, ServerProxy, Transport

class RequestTransport(Transport):
	def __init__(self, uri, cookiejar=None, use_datetime=0):
		Transport.__init__(self, use_datetime=use_datetime)

		self.opener = build_opener()

		# Parse auth (user:passwd) from the uri
		urltype, rest = splittype(uri)
		host, rest = splithost(rest)
		auth, host = splituser(host)
		self.uri = urltype + '://' + host + rest

		# Handle HTTP Basic authentication
		if auth is not None:
			user, passwd = splitpasswd(auth)
			passwdmgr = HTTPPasswordMgrWithDefaultRealm()
			passwdmgr.add_password(realm=None, uri=self.uri, user=user, passwd=passwd)
			authhandler = HTTPBasicAuthHandler(passwdmgr)
			self.opener.add_handler(authhandler)

		# Handle HTTP Cookies
		if cookiejar is not None:
			self.opener.add_handler(HTTPCookieProcessor(cookiejar))

	def request(self, host, handler, request_body, verbose=0):
		req = Request(self.uri)
		req.add_header('User-Agent', self.user_agent)
		req.add_header('Content-Type', 'text/xml')

		if hasattr(self, 'accept_gzip_encoding') and self.accept_gzip_encoding:
			req.add_header('Accept-Encoding', 'gzip')

		req.add_data(request_body)

		resp = self.opener.open(req)

		# In Python 2, resp is a urllib.addinfourl instance, which does not
		# have the getheader method that parse_response expects.
		if not hasattr(resp, 'getheader'):
			resp.getheader = resp.headers.getheader

		if resp.code == 200:
			self.verbose = verbose
			return self.parse_response(resp)

		resp.close()
		raise ProtocolError(self.uri, resp.status, resp.reason, resp.msg)

class BugzillaProxy(ServerProxy):
	def __init__(self, uri, encoding=None, verbose=0, allow_none=0,
			use_datetime=0, cookiejar=None):

		if cookiejar is None:
			cookiejar = CookieJar()

		transport = RequestTransport(use_datetime=use_datetime, uri=uri,
				cookiejar=cookiejar)
		ServerProxy.__init__(self, uri=uri, transport=transport,
				encoding=encoding, verbose=verbose, allow_none=allow_none,
				use_datetime=use_datetime)
