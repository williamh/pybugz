# Author: Mike Gilbert <floppym@gentoo.org>
# This code is released into the public domain.
# As of this writing, the Bugzilla web service is documented at the
# following URL:
# http://www.bugzilla.org/docs/4.2/en/html/api/Bugzilla/WebService.html

import http.cookiejar
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import xmlrpc.client

class RequestTransport(xmlrpc.client.Transport):
	def __init__(self, uri, cookiejar=None, use_datetime=0):
		xmlrpc.client.Transport.__init__(self, use_datetime=use_datetime)

		self.opener = urllib.request.build_opener()

		# Parse auth (user:passwd) from the uri
		urltype, rest = urllib.parse.splittype(uri)
		host, rest = urllib.parse.splithost(rest)
		auth, host = urllib.parse.splituser(host)
		self.uri = urltype + '://' + host + rest

		# Handle HTTP Basic authentication
		if auth is not None:
			user, passwd = urllib.parse.splitpasswd(auth)
			passwdmgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
			passwdmgr.add_password(realm=None, uri=self.uri, user=user, passwd=passwd)
			authhandler = urllib.request.HTTPBasicAuthHandler(passwdmgr)
			self.opener.add_handler(authhandler)

		# Handle HTTP Cookies
		if cookiejar is not None:
			self.opener.add_handler(urllib.request.HTTPCookieProcessor(cookiejar))

	def request(self, host, handler, request_body, verbose=0):
		req = urllib.request.Request(self.uri)
		req.add_header('User-Agent', self.user_agent)
		req.add_header('Content-Type', 'text/xml')

		if hasattr(self, 'accept_gzip_encoding') and self.accept_gzip_encoding:
			req.add_header('Accept-Encoding', 'gzip')

		req.data = request_body

		resp = self.opener.open(req)

		# In Python 2, resp is a urllib.addinfourl instance, which does not
		# have the getheader method that parse_response expects.
		if not hasattr(resp, 'getheader'):
			resp.getheader = resp.headers.getheader

		if resp.code == 200:
			self.verbose = verbose
			return self.parse_response(resp)

		resp.close()
		raise xmlrpc.client.ProtocolError(self.uri, resp.status, resp.reason, resp.msg)

class BugzillaProxy(xmlrpc.client.ServerProxy):
	def __init__(self, uri, encoding=None, verbose=0, allow_none=0,
			use_datetime=0, cookiejar=None):

		if cookiejar is None:
			cookiejar = http.cookiejar.CookieJar()

		transport = RequestTransport(use_datetime=use_datetime, uri=uri,
				cookiejar=cookiejar)
		xmlrpc.client.ServerProxy.__init__(self, uri=uri, transport=transport,
				encoding=encoding, verbose=verbose, allow_none=allow_none,
				use_datetime=use_datetime)
