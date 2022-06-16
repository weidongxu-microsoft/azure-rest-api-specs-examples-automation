from os import path
import sqlite3
import logging


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %X')

    example_path = 'c:/github/azure-rest-api-specs-examples'
    db_path = 'c:/github_lab/azure-rest-api-specs-examples-db/examples.db'

    with sqlite3.connect(db_path) as conn:
        conn.execute('PRAGMA foreign_keys = 1')

        cursor = conn.cursor()

        cursor.execute('select * from file')
        rows = cursor.fetchall()

        new_filenames = []
        if rows:
            for row in rows:
                filename: str = row[1]
                if '/examples-java/' in filename:
                    filename = filename.replace('.md', '.java')
                if '/examples-go/' in filename:
                    filename = filename.replace('.md', '.go')
                if '/examples-js/' in filename:
                    filename = filename.replace('.md', '.js')

                if not path.isfile(path.join(example_path, filename)):
                    raise ValueError("file not found " + filename)

                new_filenames.append((filename, row[0]))

        cursor.executemany('update file set file = ? where id = ?', new_filenames)

        conn.commit()


if __name__ == '__main__':
    main()
