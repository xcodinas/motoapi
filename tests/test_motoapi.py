import unittest

from motoapi import motoapi, db
from manage import create_user

TEST_DB = 'test.db'


class MotoApiTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        motoapi.config['TESTING'] = True
        motoapi.config['WTF_CSRF_ENABLED'] = False
        motoapi.config['DEBUG'] = False
        cls.motoapi = motoapi
        cls.client = motoapi.test_client()

        db.create_all()

        super().setUpClass()

    def login(self, email, password):
        return self.client.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_example_page_unlogged(self):
        response = self.client.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            MotoApiTestCase))
    return suite
