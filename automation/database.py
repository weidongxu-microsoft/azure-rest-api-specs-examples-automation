from datetime import datetime
import sqlite3
import logging
from typing import List

from models import Release


SCRIPT_QUERY_RELEASE = '''select name from release where name = ? and language = ?'''
SCRIPT_INSERT_RELEASE = '''insert or replace into release (name, language, tag, package, version, date_epoch) values (?, ?, ?, ?, ?, ?)'''
SCRIPT_INSERT_FILE = '''insert or replace into file (file, release_id) values (?, ?)'''

SCRIPT_QUERY_RELEASE_DETAIL = '''select tag, package, version, date_epoch from release where language = ?'''


class Database:
    database_path: str

    def __init__(self, database_path: str):
        self.database_path = database_path

    def new_release(self, name: str, language: str, tag: str, package: str, version: str, date: datetime,
                    files: List[str]) -> bool:
        # add a new release and all the example files
        # return false, if release already exists in DB

        date_epoch = int(date.timestamp())
        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.execute('PRAGMA foreign_keys = 1')

                cursor = conn.cursor()
                cursor.execute(SCRIPT_QUERY_RELEASE, (name, language))
                existing_release = cursor.fetchone()
                if existing_release:
                    logging.warning(f'Release already exists for {language}#{name}')
                    return False

                cursor = conn.cursor()
                cursor.execute(SCRIPT_INSERT_RELEASE, (name, language, tag, package, version, date_epoch))
                release_id = cursor.lastrowid

                file_records = [(file, release_id) for file in files]
                cursor.executemany(SCRIPT_INSERT_FILE, file_records)

                conn.commit()
            return True
        except sqlite3.Error as error:
            logging.error(f'Database error: {error}')
            return False

    def query_releases(self, language: str) -> List[Release]:
        try:
            releases = []
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute(SCRIPT_QUERY_RELEASE_DETAIL, (language,))
                release_rows = cursor.fetchall()
                if release_rows:
                    for row in release_rows:
                        date = datetime.fromtimestamp(row[3])
                        releases.append(Release(row[0], row[1], row[2], date))
            return releases
        except sqlite3.Error as error:
            logging.error(f'Database error: {error}')
            return []
