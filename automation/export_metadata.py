import sys
from os import path
import argparse
import sqlite3
import logging
import csv
import datetime
import subprocess
import re
from github import GitHubRepository


example_repo: str = 'https://github.com/Azure/azure-rest-api-specs-examples'
example_folder: str = 'example'
metadata_branch: str = 'metadata'

automation_repo: str = 'https://github.com/weidongxu-microsoft/azure-rest-api-specs-examples-automation'
database_branch: str = 'database'
database_folder: str = 'db'
database_filename: str = 'examples.db'


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %X')

    script_path = path.abspath(path.dirname(sys.argv[0]))
    root_path = path.abspath(path.join(script_path, '..'))

    # argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--github-token', type=str, required=True,
                        help='GitHub token')
    args = parser.parse_args()

    github_token = args.github_token

    # checkout metadata branch from azure-rest-api-specs-examples repo
    example_metadata_path = path.join(root_path, example_folder)
    cmd = ['git', 'clone',
           '--quiet',
           '--depth', '1',
           '--branch', metadata_branch,
           example_repo, example_metadata_path]
    logging.info(f'Checking out repository: {example_repo}, branch {metadata_branch}')
    logging.info('Command line: ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=root_path)

    # checkout database
    database_path = path.join(root_path, database_folder)
    cmd = ['git', 'clone',
           '--quiet',
           '--branch', database_branch,
           automation_repo, database_path]
    logging.info(f'Checking out repository: {automation_repo}, branch {database_branch}')
    logging.info('Command line: ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=root_path)

    # export metadata from db to csv
    db_file_path = path.join(database_path, database_filename)

    index_file_path = path.join(example_metadata_path, 'java-library-example-index.csv')
    list_file_path = path.join(example_metadata_path, 'java-library-example-list.csv')

    with sqlite3.connect(db_file_path) as conn:
        conn.execute('PRAGMA foreign_keys = 1')

        cursor = conn.cursor()

        with open(index_file_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(['id', 'name', 'language', 'tag', 'package', 'version', 'date_epoch', 'date'])

            cursor.execute('select * from release'
                           # ' where language is "java"'
                           ' order by id')
            rows = cursor.fetchall()

            if rows:
                for row in rows:
                    date_epoch = row[-1]
                    date = datetime.datetime.fromtimestamp(date_epoch)
                    csv_writer.writerow(row + (date.strftime('%m/%d/%Y'),))

        with open(list_file_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(['id', 'file', 'release_id'])

            cursor.execute('select file.id, file.file, file.release_id from file'
                           ' join release on file.release_id = release.id'
                           # ' where release.language is "java"'
                           ' order by file.id')
            rows = cursor.fetchall()

            if rows:
                for row in rows:
                    csv_writer.writerow(row)

    # git add
    cmd = ['git', 'add', 'java-library-example-index.csv']
    logging.info('Command line: ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=example_metadata_path)

    cmd = ['git', 'add', 'java-library-example-list.csv']
    logging.info('Command line: ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=example_metadata_path)

    # git checkout new branch
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    branch = f'automation-metadata-{date_str}'
    cmd = ['git', 'checkout', '-b', branch]
    logging.info('Command line: ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=example_metadata_path)

    # git commit
    title = f'[Automation] Update metadata on {date_str}'
    logging.info(f'git commit: {title}')
    cmd = ['git',
           '-c', 'user.name=azure-sdk',
           '-c', 'user.email=azuresdk@microsoft.com',
           'commit', '-m', title]
    logging.info('Command line: ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=example_metadata_path)

    # git push
    remote_uri = 'https://' + github_token + '@' + example_repo[len('https://'):]
    cmd = ['git', 'push', remote_uri, branch]
    # do not print this as it contains token
    # logging.info('Command line: ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=example_metadata_path)

    # create github pull request
    owner = repository_owner(example_repo)
    name = repository_name(example_repo)
    head = f'{owner}:{branch}'
    repo = GitHubRepository(owner, name, github_token)
    pull_number = repo.create_pull_request(title, head, metadata_branch)
    logging.info(f'Pull number {pull_number}')


def repository_owner(repository: str) -> str:
    return re.match(r'https://github.com/([^/:]+)/.*', repository).group(1)


def repository_name(repository: str) -> str:
    return re.match(r'https://github.com/[^/:]+/(.*)', repository).group(1)


if __name__ == '__main__':
    main()
