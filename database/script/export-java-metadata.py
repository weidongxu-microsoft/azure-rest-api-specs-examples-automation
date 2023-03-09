from os import path
import sqlite3
import logging
import csv
import datetime


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %X')

    example_path = 'c:/github/azure-rest-api-specs-examples'
    db_path = 'c:/github_lab/azure-rest-api-specs-examples-db/examples.db'

    with sqlite3.connect(db_path) as conn:
        conn.execute('PRAGMA foreign_keys = 1')

        cursor = conn.cursor()

        with open('java-library-example-index.csv', 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(['id', 'name', 'language', 'tag', 'package', 'version', 'date_epoch', 'date'])

            cursor.execute('select * from release where language is "java" order by id')
            rows = cursor.fetchall()

            if rows:
                for row in rows:
                    date_epoch = row[-1]
                    date = datetime.datetime.fromtimestamp(date_epoch)
                    csv_writer.writerow(row + (date.strftime('%m/%d/%Y'),))

        with open('java-library-example-list.csv', 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(['id', 'file', 'release_id'])

            cursor.execute('select file.id, file.file, file.release_id from file'
                           ' join release on file.release_id = release.id'
                           ' where release.language is "java"'
                           ' order by file.id')
            rows = cursor.fetchall()

            if rows:
                for row in rows:
                    csv_writer.writerow(row)


if __name__ == '__main__':
    main()
