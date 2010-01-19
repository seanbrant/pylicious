import datetime
import hashlib
import os
import time
import urllib
import urllib2
from xml.dom import minidom

__version__ = 'pre-1.0'

USER_AGENT = 'Pylicious Pyhton Delicious Client/%s' % __version__

DELICIOUS_V1_API_BASE_URL = 'https://api.del.icio.us/v1/'

DELICIOUS_V1_ENDPOINTS = {
    'posts/update': '%sposts/update' % DELICIOUS_V1_API_BASE_URL,
    'posts/add': '%sposts/add' % DELICIOUS_V1_API_BASE_URL,
    'posts/delete': '%sposts/delete' % DELICIOUS_V1_API_BASE_URL,
    'posts/get': '%sposts/get' % DELICIOUS_V1_API_BASE_URL,
}

TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class DeliciousClientError(Exception):
    """Base Delicious Error"""
    pass


class EndpointDoesNotExist(DeliciousClientError):
    """Error finding the url endpoint"""
    pass


class ThrottleError(DeliciousClientError):
    """Error caused by Delicious throttling requests"""

    def __init__(self, url):
        self.url = url

    def __str__(self):
        return "Delicious throttled requests to %s" & self.url


class AddError(DeliciousClientError):
    """Error adding post to Delicious"""
    pass


class DeleteError(DeliciousClientError):
    """Error delete post on Delicious"""
    pass


class HumanizedBoolean(object):

    def __init__(self, boolean):
        self.boolean = boolean

    def __repr__(self):
        if self.boolean:
            return 'yes'
        return 'no'


class BaseDeliciousClient(object):

    # Used to keep track of requests for throttling
    _last_request_time = None

    # Subclasses override this with a dict of endpoints
    _endpoints = {}

    def _request(self, url, params={}):
        if self._last_request_time and (self._last_request_time - \
            time.time()) > 2:
            # We need to chill a bit as to not upset Yahoo
            time.sleep(1)
        self._last_request_time = time.time()
        if params:
            url = '%s?%s' % (url, urllib.urlencode(params))
        response = self.urlopen(url)
        if response.headers.status in ['503', '999']:
            raise ThrottleError(url)
        return minidom.parseString(response.read())

    def urlopen(self, url):
        raise NotImplementedError("Subclasses of BaseDeliciousClient " \
            "must define urlopen")

    def get_endpoint_url(self, key):
        try:
            return self._endpoints[key]
        except KeyError:
            raise EndpointDoesNotExist("Could not " \
                "find endpoint for %s" % key)

    def last_update(self):
        """
        Returns the last update datetime for the user,
        as well as the number of new items in the user's
        inbox since it was last visited.
        """
        xml = self._request(self.get_endpoint_url('posts/update'))
        time = datetime.datetime.strptime(xml.firstChild.getAttribute('time'),
            TIME_FORMAT)
        inboxnew = int(xml.firstChild.getAttribute('inboxnew'))
        return (time, inboxnew)

    def add(self, url, description, extended='', tags=[], dt=None,
        replace=False, shared=False):
        params = {
            'url': url,
            'description': description,
        }
        if extended:
            if not isinstance(extended, basestring):
                raise TypeError("extended must be a string not %s"
                    % extended.__class__)
            params['extended'] = unicode(extended)
        if tags:
            if not isinstance(tags, list) and not isinstance(tags, tuple):
                raise TypeError("tags must be a list or a tuple not %s" %
                    tags.__class__)
        if dt:
            if not isinstance(dt, datetime.datetime):
                raise TypeError("dt must be a datetime object not %s" %
                    dt.__class__)
            params['dt'] = dt.strftime(TIME_FORMAT)
        params['replace'] = HumanizedBoolean(replace)
        params['shared'] = HumanizedBoolean(shared)
        xml = self._request(self.get_endpoint_url('posts/add'), params)
        if not xml.firstChild.getAttribute('code').startswith('done'):
            raise AddError
        return True

    def delete(self, url):
        params = {'url': url}
        xml = self._request(self.get_endpoint_url('posts/delete'), params)
        if not xml.firstChild.getAttribute('code').startswith('done'):
            raise DeleteError
        return True

    def get(self, tags=[], dt=None, urls=[], meta=True):
        params = {}
        if tags:
            if not isinstance(tags, list) and not isinstance(tags, tuple):
                raise TypeError("tags must be a list or a tuple not %s" %
                    tags.__class__)
            params['tags'] = '+'.join(tags)
        if dt:
            if not isinstance(dt, datetime.datetime):
                raise TypeError("dt must be a datetime object not %s" %
                    dt.__class__)
            params['dt'] = dt.strftime(TIME_FORMAT)
        if urls:
            if len(urls) == 1:
                print urls[0]
                params['url'] = urllib.quote(urls[0])
            else:
                params['hashes'] = '+'.join([hashlib.md5(url).hexdigest() \
                    for url in urls])
        params['meta'] = HumanizedBoolean(meta)
        xml = self._request(self.get_endpoint_url('posts/get'), params)
        print xml


class HttpAuthDeliciousClient(BaseDeliciousClient):

    _endpoints = DELICIOUS_V1_ENDPOINTS

    def __init__(self, username, password):
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password('del.icio.us API',
            DELICIOUS_V1_API_BASE_URL, username, password)
        opener = urllib2.build_opener(auth_handler)
        opener.addheaders = [('User-agent', USER_AGENT)]
        self.urllib = urllib2
        self.urllib.install_opener(opener)

    def urlopen(self, url):
        return self.urllib.urlopen(url)
