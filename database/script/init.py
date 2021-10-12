import sys
from os import path
import sqlite3
import logging


SCRIPT_RELEASE_TABLE = '''create table release (
    id          integer         not null primary key,
    name        varchar(255)    not null,
    language    varchar(255)    not null,
    repository  varchar(2048)   not null,
    tag         varchar(255)    not null,
    package     varchar(255)    not null,
    version     varchar(255)    not null,
    
    unique(name, language)
)'''


SCRIPT_RELEASE_INDEX1 = 'create index release_idx1 on release(language, package, version)'


SCRIPT_FILE_TABLE = '''create table file (
    id          integer         not null primary key,
    file        varchar(2048)   not null,
    release_id  integer         not null,

    foreign key(release_id) references release(id)
        on delete cascade
        
    unique(file)
)'''


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %X')

    script_path = path.abspath(path.dirname(sys.argv[0]))
    root_path = path.abspath(path.join(script_path, '../..'))
    db_path = path.join(root_path, 'database/examples.db')

    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(SCRIPT_RELEASE_TABLE)
        cur.execute(SCRIPT_RELEASE_INDEX1)
        cur.execute(SCRIPT_FILE_TABLE)


if __name__ == '__main__':
    main()
