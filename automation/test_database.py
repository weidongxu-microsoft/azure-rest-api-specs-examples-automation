import unittest

from datetime import datetime
from database import Database
import sqlite3


class TestDatabase(unittest.TestCase):

    def test_insert(self):
        name = 'com.azure.resourcemanager:mock-sdk:1.0.0-beta.1'
        language = 'java'

        database = Database('../database/examples.db')
        succeeded = database.new_release(
            name, language, 'release_tag1', 'mock-sdk', '1.0.0-beta.1', datetime.now(), ['file1', 'file2'])
        self.assertTrue(succeeded)

        succeeded = database.new_release(
            name, language, 'release_tag1', 'mock-sdk', '1.0.0-beta.1', datetime.now(), ['file3'])
        self.assertFalse(succeeded)

        # clean up
        with sqlite3.connect('../database/examples.db') as conn:
            conn.execute("PRAGMA foreign_keys = 1")
            conn.execute('delete from release where name = ? and language = ?', (name, language))
            conn.commit()
