import unittest

import sys
import os
from datetime import datetime
from database import Database
import sqlite3

sys.path.append('../database/script')

from init import script1


class TestDatabase(unittest.TestCase):

    def test_insert(self):
        # init database
        os.remove('test.db')
        with sqlite3.connect('test.db') as conn:
            script1(conn.cursor())

        name = 'com.azure.resourcemanager:mock-sdk:1.0.0-beta.1'
        language = 'java'

        database = Database('test.db')
        succeeded = database.new_release(
            name, language, 'release_tag1', 'mock-sdk', '1.0.0-beta.1', datetime.now(), ['file1', 'file2'])
        self.assertTrue(succeeded)

        succeeded = database.new_release(
            name, language, 'release_tag1', 'mock-sdk', '1.0.0-beta.1', datetime.now(), ['file3'])
        self.assertFalse(succeeded)
