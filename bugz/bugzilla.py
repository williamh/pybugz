# Author: Mike Gilbert <floppym@gentoo.org>
# This code is released into the public domain.
# As of this writing, the Bugzilla web service is documented at the
# following URL:
# http://www.bugzilla.org/docs/4.2/en/html/api/Bugzilla/WebService.html

from cookielib import CookieJar
from urllib2 import Request, build_opener, HTTPCookieProcessor
from xmlrpclib import ProtocolError, ServerProxy, Transport

class RequestTransport(Transport):
	def __init__(self, uri, cookies, use_datetime=0):
		Transport.__init__(self, use_datetime=use_datetime)
		self.uri = uri
		self.opener = build_opener(HTTPCookieProcessor(cookies))

	def request(self, host, handler, request_body, verbose=0):
		req = Request(self.uri)
		req.add_header('User-Agent', self.user_agent)
		req.add_header('Content-Type', 'text/xml')
		req.add_data(request_body)
		resp = self.opener.open(req)
		if resp.code == 200:
			self.verbose = verbose
			return self.parse_response(resp)
		resp.close()
		raise ProtocolError(self.uri, resp.status, resp.reason, resp.msg)

class BugzillaProxy(ServerProxy):
	def __init__(self, uri, encoding=None, verbose=0, allow_none=0,
			use_datetime=0, cookies=None):

		if cookies is None:
			cookies = CookieJar()

		transport = RequestTransport(use_datetime=use_datetime, uri=uri,
				cookies=cookies)
		ServerProxy.__init__(self, uri=uri, transport=transport,
				encoding=encoding, verbose=verbose, allow_none=allow_none,
				use_datetime=use_datetime)
