import datetime
import sys
import time
import unittest

from pylicious import HttpAuthDeliciousClient, DeliciousPost, DeliciousDate


class HttpAuthDeliciousClientTestCaseConfigException(Exception):
    pass


class HttpAuthDeliciousClientTestCase(unittest.TestCase):

    def setUp(self):
        try:
            from test_config import DELICIOUS_USERNAME, DELICIOUS_PASSWORD
        except ImportError:
            raise HttpAuthDeliciousClientTestCaseConfigException("You need " \
                "to create a test_config module on your python path " \
                "that defines DELICIOUS_USERNAME, and DELICIOUS_PASSWORD.")

        self.client = HttpAuthDeliciousClient(
            DELICIOUS_USERNAME, DELICIOUS_PASSWORD)
        self.url = 'http://google.com'

    def test_last_update_call(self):
        time, count = self.client.last_update()
        self.assertTrue(isinstance(time, datetime.datetime))
        self.assertTrue(isinstance(count, int))

    def test_add_call(self):
        self.client.add(self.url, 'Googles homepage')
        self.client.add(self.url, 'Googles homepage',
            extended='Some more text', tags=['google', 'whitespace'],
            dt=datetime.datetime.now(), replace=True, shared=False)

    def test_delete_call(self):
        self.client.delete(self.url)

    def test_get_call(self):
        posts = self.client.get()
        self.assertTrue(isinstance(posts[0], DeliciousPost))

    def test_recent_call(self):
        posts = self.client.recent()
        self.assertTrue(isinstance(posts[0], DeliciousPost))

    def test_dates_call(self):
        dates = self.client.dates()
        self.assertTrue(isinstance(dates[0], DeliciousDate))

    def test_all_call(self):
        pass
        #posts = self.client.all()
        #self.assertTrue(isinstance(posts[0], DeliciousPost))

    def test_hashes_call(self):
        pass
        #posts = self.client.hashes()
        #self.assertTrue(isinstance(posts[0], DeliciousPost))
