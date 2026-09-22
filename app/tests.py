import os
import unittest


class DjangoMigrationSmokeTest(unittest.TestCase):
    def test_manage_py_exists(self):
        self.assertTrue(os.path.exists(os.path.join(os.getcwd(), 'manage.py')))
