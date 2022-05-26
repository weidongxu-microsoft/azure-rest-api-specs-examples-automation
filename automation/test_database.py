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
        try:
            os.remove('test.db')
        except OSError:
            pass
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

    def test_query(self):
        # init database
        try:
            os.remove('test.db')
        except OSError:
            pass
        with sqlite3.connect('test.db') as conn:
            script1(conn.cursor())

        # populate db
        database = Database('test.db')
        succeeded = database.new_release(
            'com.azure.resourcemanager:mock-sdk:1.0.0-beta.1',
            'java', 'release_tag1', 'mock-sdk', '1.0.0-beta.1', datetime.now(), ['file1', 'file2'])
        self.assertTrue(succeeded)

        succeeded = database.new_release(
            'com.azure.resourcemanager:mock-sdk:1.0.0-beta.2',
            'java', 'release_tag2', 'mock-sdk', '1.0.0-beta.2', datetime.now(), ['file3'])
        self.assertTrue(succeeded)

        succeeded = database.new_release(
            'github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/mock-sdk-go@v0.5.0',
            'go', 'release_tag3', 'mock-sdk-go', '0.5.0', datetime.now(), ['file1_go'])
        self.assertTrue(succeeded)

        # query
        releases = database.query_releases('java')
        self.assertEqual(2, len(releases))

        releases = database.query_releases('go')
        self.assertEqual(1, len(releases))
        self.assertEqual('release_tag3', releases[0].tag)
        self.assertEqual('mock-sdk-go', releases[0].package)
        self.assertEqual('0.5.0', releases[0].version)
