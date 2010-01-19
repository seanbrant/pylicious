import datetime
import sys
import unittest

from pylicious import HttpAuthDeliciousClient


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
        self.client.get(tags=['google'], urls=[self.url])
        self.client.get(tags=['google', 'google'], dt=datetime.datetime.now(),
            urls=[self.url, self.url], meta=False)
