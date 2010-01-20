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
    'posts/recent': '%sposts/recent' % DELICIOUS_V1_API_BASE_URL,
    'posts/dates': '%sposts/dates' % DELICIOUS_V1_API_BASE_URL,
    'posts/all': '%sposts/all' % DELICIOUS_V1_API_BASE_URL,
    'posts/hashes': '%sposts/all?hashes' % DELICIOUS_V1_API_BASE_URL,
}

DATE_FORMAT_ISO = '%Y-%m-%dT%H:%M:%SZ'
DATE_FORMAT_SHORT = '%Y-%m-%d'


class DeliciousClientError(Exception):
    """Base Delicious Error"""
    pass


class EndpointDoesNotExist(DeliciousClientError):
    """Error finding the url endpoint"""
    pass


class ThrottleError(DeliciousClientError):
    """Error caused by throttling requests"""

    def __init__(self, url):
        self.url = url

    def __str__(self):
        return " Throttled requests to %s" % self.url


class ValidationError(DeliciousClientError):
    """Error when data does not validate"""
    pass


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


class DeliciousPost(object):

    def __init__(self, client, href, meta, description=None,
        extended=None, hash=None, others=None, tags=None, time=None):
        self.client = client
        self.url = href
        self.description = description
        self.extended = extended
        self.hash = hash
        self.meta = meta
        self.others = others
        self.tags = tags
        self.time = time
        if self.tags:
            self.tags = tags.split(' ')
        if self.time:
            self.time = datetime.datetime.strptime(time, DATE_FORMAT_ISO)

    @classmethod
    def create_posts(cls, client, xml):
        return [cls(
            client=client,
            href=post.getAttribute('href'),
            description=post.getAttribute('description'),
            extended=post.getAttribute('extended'),
            hash=post.getAttribute('hash'),
            meta=post.getAttribute('meta'),
            others=post.getAttribute('others'),
            tags=post.getAttribute('tags'),
            time=post.getAttribute('time'),
        ) for post in xml]

    @classmethod
    def create_posts_from_hashes(cls, client, xml):
        return [cls(
            client=client,
            href=post.getAttribute('url'),
            meta=post.getAttribute('meta'),
        ) for post in xml]


class DeliciousDate(object):

    def __init__(self, client, count, date):
        self.client = client
        self.count = int(count)
        self.date = datetime.datetime.strptime(date, DATE_FORMAT_SHORT)

    @classmethod
    def create_dates(cls, client, xml):
        return [cls(
            client=client,
            count=date.getAttribute('count'),
            date=date.getAttribute('date'),
        ) for date in xml]


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
            DATE_FORMAT_ISO)
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
                raise ValidationError("extended must be a string not %s"
                    % extended.__class__)
            params['extended'] = unicode(extended)
        if tags:
            if not isinstance(tags, list) and not isinstance(tags, tuple):
                raise ValidationError("tags must be a list or a tuple not %s" %
                    tags.__class__)
        if dt:
            if not isinstance(dt, datetime.datetime):
                raise ValidationError("dt must be a datetime object not %s" %
                    dt.__class__)
            params['dt'] = dt.strftime(DATE_FORMAT_ISO)
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
                raise ValidationError("tags must be a list or a tuple not %s" %
                    tags.__class__)
            params['tags'] = '+'.join(tags)
        if dt:
            if not isinstance(dt, datetime.datetime):
                raise ValidationError("dt must be a datetime object not %s" %
                    dt.__class__)
            params['dt'] = dt.strftime(DATE_FORMAT_ISO)
        if urls:
            if len(urls) == 1:
                params['url'] = urllib.quote(urls[0])
            else:
                params['hashes'] = '+'.join([hashlib.md5(url).hexdigest() \
                    for url in urls])
        params['meta'] = HumanizedBoolean(meta)
        xml = self._request(self.get_endpoint_url('posts/get'), params)
        return DeliciousPost.create_posts(self,
            xml.getElementsByTagName('post'))

    def recent(self, tag=None, count=15):
        params = {}
        if tag:
            params['tag'] = unicode(tag)
        if count > 100 or count < 1:
            raise ValidationError("count must be between 1 and 100 not %s"
                % count)
        xml = self._request(self.get_endpoint_url('posts/recent'), params)
        return DeliciousPost.create_posts(self,
            xml.getElementsByTagName('post'))

    def dates(self, tag=None):
        params = {}
        if tag:
            params['tag'] = unicode(tag)
        xml = self._request(self.get_endpoint_url('posts/dates'), params)
        return DeliciousDate.create_dates(self,
            xml.getElementsByTagName('date'))

    def all(self, tag=None, start=None, results=None,
        fromdt=None, todt=None, meta=True):
        params = {}
        if tag:
            params['tag'] = unicode(tag)
        if start:
            try:
                params['start'] = int(start)
            except ValueError:
                raise ValidationError("start must be an integer not a %s" %
                    start.__class__)
        if results:
            try:
                params['results'] = int(results)
            except ValueError:
                raise ValidationError("results must be an integer not a %s" %
                    results.__class__)
        if fromdt:
            if not isinstance(fromdt, datetime.datetime):
                raise ValidationError("fromdt must be a datetime object " \
                    "not %s" % fromdt.__class__)
            params['fromdt'] = fromdt.strftime(DATE_FORMAT_ISO)
        if todt:
            if not isinstance(todt, datetime.datetime):
                raise ValidationError("todt must be a datetime object not %s" %
                    todt.__class__)
            params['todt'] = todt.strftime(DATE_FORMAT_ISO)
        params['meta'] = HumanizedBoolean(meta)
        xml = self._request(self.get_endpoint_url('posts/all'), params)
        return DeliciousPost.create_posts(self,
            xml.getElementsByTagName('post'))

    def hashes(self):
        xml = self._request(self.get_endpoint_url('posts/hashes'))
        return DeliciousPost.create_posts(self,
            xml.getElementsByTagName('post'))


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
        try:
            return self.urllib.urlopen(url)
        except self.urllib.HTTPError, e:
            # Need to test this to make sure it works
            raise ThrottleError(url)
