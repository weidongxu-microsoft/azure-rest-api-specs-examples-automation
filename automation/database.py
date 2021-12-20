from datetime import datetime
import sqlite3
import logging
from typing import List


SCRIPT_QUERY_RELEASE = '''select name from release where name = ? and language = ?'''
SCRIPT_INSERT_RELEASE = '''insert or replace into release (name, language, tag, package, version, date_epoch) values (?, ?, ?, ?, ?, ?)'''
SCRIPT_INSERT_FILE = '''insert or replace into file (file, release_id) values (?, ?)'''


class Database:
    database_path: str

    def __init__(self, database_path: str):
        self.database_path = database_path

    def new_release(self, name: str, language: str, tag: str, package: str, version: str, date: datetime,
                    files: List[str]) -> bool:
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
