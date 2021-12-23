import os
import shutil
from os import path
import sys
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
import json
import re
import argparse
import logging
import dataclasses
from typing import List, Dict
import itertools
import requests
try:
    from database import Database
except ImportError:
    pass


github_token: str
root_path: str = '.'

clean_tmp_dir: bool = True
tmp_folder: str = 'tmp'
tmp_spec_folder: str = 'spec'
tmp_example_folder: str = 'example'
tmp_sdk_folder: str = 'sdk'

automation_repo = 'https://github.com/weidongxu-microsoft/azure-rest-api-specs-examples-automation'
database_branch = 'database'
database_folder = 'db'


@dataclasses.dataclass(eq=True, frozen=True)
class ReleaseTagConfiguration:
    regex_match: str
    package_regex_group: str
    version_regex_group: str


@dataclasses.dataclass(eq=True)
class Script:
    run: str


@dataclasses.dataclass(eq=True, frozen=True)
class SdkConfiguration:
    name: str
    language: str
    repository: str
    release_tag: ReleaseTagConfiguration
    script: Script

    @property
    def repository_owner(self) -> str:
        return re.match(r'https://github.com/([^/:]+)/.*', self.repository).group(1)

    @property
    def repository_name(self) -> str:
        return re.match(r'https://github.com/[^/:]+/(.*)', self.repository).group(1)


@dataclasses.dataclass(eq=True, frozen=True)
class OperationConfiguration:
    sdk_examples_repository: str
    build_id: str
    persist_data: bool
    date_start: datetime
    date_end: datetime

    @property
    def repository_owner(self) -> str:
        return re.match(r'https://github.com/([^/:]+)/.*', self.sdk_examples_repository).group(1)

    @property
    def repository_name(self) -> str:
        return re.match(r'https://github.com/[^/:]+/(.*)', self.sdk_examples_repository).group(1)


@dataclasses.dataclass(eq=True, frozen=True)
class Configuration:
    operation: OperationConfiguration
    sdks: List[SdkConfiguration]


@dataclasses.dataclass(eq=True, frozen=True)
class CommandLineConfiguration:
    build_id: str
    release_in_days: int
    language: str
    persist_data: bool
    merge_pr: bool


@dataclasses.dataclass(eq=True, frozen=True)
class Release:
    tag: str
    package: str
    version: str
    date: datetime


@dataclasses.dataclass(eq=True, frozen=True)
class AggregatedError:
    errors: List[Exception]


def load_configuration(command_line: CommandLineConfiguration) -> Configuration:
    with open(path.join(root_path, 'automation/configuration.json'), 'r', encoding='utf-8') as f_in:
        config = json.load(f_in)

    now = datetime.now(timezone.utc)
    operation_configuration = OperationConfiguration(config['sdkExample']['repository'],
                                                     command_line.build_id,
                                                     command_line.persist_data,
                                                     now - timedelta(days=command_line.release_in_days), now)

    sdk_configurations = []
    for sdk_config in config['sdkConfigurations']:
        script = Script(sdk_config['script']['run'])
        release_tag = ReleaseTagConfiguration(sdk_config['releaseTag']['regexMatch'],
                                              sdk_config['releaseTag']['packageRegexGroup'],
                                              sdk_config['releaseTag']['versionRegexGroup'])
        sdk_configuration = SdkConfiguration(sdk_config['name'],
                                             sdk_config['language'],
                                             sdk_config['repository'],
                                             release_tag, script)
        sdk_configurations.append(sdk_configuration)

    return Configuration(operation_configuration, sdk_configurations)


def create_pull_request(operation: OperationConfiguration, title: str, head: str):
    logging.info(f'Create pull request: {head}')

    request_uri = f'https://api.github.com/repos/{operation.repository_owner}/{operation.repository_name}/pulls'
    request_body = {
        'title': title,
        'head': head,
        'base': 'main'
    }
    pull_request_response = requests.post(request_uri,
                                          json=request_body,
                                          headers={'Authorization': f'token {github_token}'})
    if pull_request_response.status_code == 201:
        logging.info('Pull request created')
    else:
        logging.error(f'Request failed: {pull_request_response.status_code}\n{pull_request_response.json()}')


def list_pull_requests(operation: OperationConfiguration) -> List[Dict]:
    logging.info(f'List pull requests')

    request_uri = f'https://api.github.com/repos/{operation.repository_owner}/{operation.repository_name}/pulls' \
                  f'?per_page=100'
    pull_request_response = requests.get(request_uri,
                                         headers={'Authorization': f'token {github_token}'})
    if pull_request_response.status_code == 200:
        logging.info('Pull request created')
        return pull_request_response.json()
    else:
        logging.error(f'Request failed: {pull_request_response.status_code}\n{pull_request_response.json()}')
        return []


def merge_pull_request(operation: OperationConfiguration, pull_request: Dict):
    title = pull_request['title']
    logging.info(f'Merge pull request: {title}')

    pull_number = pull_request['number']

    request_uri = f'https://api.github.com/repos/{operation.repository_owner}/{operation.repository_name}' \
                  f'/pulls/{pull_number}/merge'
    request_body = {
        'commit_title': title
    }
    pull_request_response = requests.put(request_uri,
                                         json=request_body,
                                         headers={'Authorization': f'token {github_token}'})
    if pull_request_response.status_code == 200:
        logging.info('Pull request merged')
    else:
        logging.error(f'Request failed: {pull_request_response.status_code}\n{pull_request_response.json()}')


def merge_pull_requests(operation: OperationConfiguration):
    logging.info('Merge pull requests')

    pull_requests = list_pull_requests(operation)
    for pull_request in pull_requests:
        title = pull_request['title']
        if title.startswith('[Automation]'):
            merge_pull_request(operation, pull_request)
            # wait a few seconds to avoid 409
            time.sleep(5)


def process_release(operation: OperationConfiguration, sdk: SdkConfiguration, release: Release,
                    aggregated_error: AggregatedError):
    # process per release

    logging.info(f'Processing release: {release.tag}')

    tmp_root_path = path.join(root_path, tmp_folder)
    os.makedirs(tmp_root_path, exist_ok=True)
    tmp_path = tempfile.mkdtemp(prefix='tmp', dir=tmp_root_path)
    logging.info(f'Work directory: {tmp_path}')
    try:
        example_repo_path = path.join(tmp_path, tmp_example_folder)
        sdk_repo_path = path.join(tmp_path, tmp_sdk_folder)
        spec_repo_path = path.join(tmp_root_path, tmp_spec_folder)

        # checkout azure-rest-api-specs-examples repo
        cmd = ['git', 'clone',
               '--quiet',
               '--depth', '1',
               operation.sdk_examples_repository, example_repo_path]
        logging.info(f'Checking out repository: {operation.sdk_examples_repository}')
        logging.info('Command line: ' + ' '.join(cmd))
        subprocess.check_call(cmd, cwd=tmp_path)

        # checkout sdk repo
        cmd = ['git', 'clone',
               '-c', 'advice.detachedHead=false',
               '--quiet',
               '--depth', '1',
               '--branch', release.tag,
               sdk.repository, sdk_repo_path]
        logging.info(f'Checking out repository: {sdk.repository}')
        logging.info('Command line: ' + ' '.join(cmd))
        subprocess.check_call(cmd, cwd=tmp_path)

        # prepare input.json
        input_json_path = path.join(tmp_path, 'input.json')
        output_json_path = path.join(tmp_path, 'output.json')
        with open(input_json_path, 'w', encoding='utf-8') as f_out:
            input_json = {
                'specsPath': spec_repo_path,
                'sdkExamplesPath': example_repo_path,
                'sdkPath': sdk_repo_path,
                'tempPath': tmp_path,
                'release': {
                    'tag': release.tag,
                    'package': release.package,
                    'version': release.version
                }
            }
            logging.info(f'Input JSON for worker: {input_json}')
            json.dump(input_json, f_out, indent=2)

        # run script
        logging.info(f'Running worker: {sdk.script.run}')
        start = time.perf_counter()
        subprocess.check_call([sdk.script.run, input_json_path, output_json_path], cwd=root_path)
        end = time.perf_counter()
        logging.info(f'Worker ran: {str(timedelta(seconds=end-start))}')

        # parse output.json
        release_name = release.tag
        succeeded = True
        if path.isfile(output_json_path):
            with open(output_json_path, 'r', encoding='utf-8') as f_in:
                output = json.load(f_in)
                logging.info(f'Output JSON from worker: {output}')
                release_name = output['name']
                succeeded = ('succeeded' == output['status'])

        if not succeeded:
            aggregated_error.errors.append(RuntimeError(f'Worker failed for release tag: {release.tag}'))
            return

        # commit and create pull request
        # check for new examples
        cmd = ['git', 'status', '--porcelain']
        logging.info('Command line: ' + ' '.join(cmd))
        output = subprocess.check_output(cmd, cwd=example_repo_path)
        if len(output) == 0:
            logging.info(f'No change to repository: {example_repo_path}')
        else:
            output_str = str(output, 'utf-8')
            logging.info(f'git status:\n{output_str}')

            # git add
            cmd = ['git', 'add', '--all']
            logging.info('Command line: ' + ' '.join(cmd))
            subprocess.check_call(cmd, cwd=example_repo_path)

            # find added/modified files
            cmd = ['git', 'status', '--porcelain']
            logging.info('Command line: ' + ' '.join(cmd))
            output = subprocess.check_output(cmd, cwd=example_repo_path)
            output_str = str(output, 'utf-8')
            changed_files = [file.strip()[3:] for file in output_str.splitlines()]

            # git checkout new branch
            branch = f'automation-examples_{sdk.name}_{release.tag}_{operation.build_id}'
            cmd = ['git', 'checkout', '-b', branch]
            logging.info('Command line: ' + ' '.join(cmd))
            subprocess.check_call(cmd, cwd=example_repo_path)

            # git commit
            title = f'[Automation] Collect examples from {sdk.name}#{release.tag}'
            logging.info(f'git commit: {title}')
            cmd = ['git',
                   '-c', 'user.name=azure-sdk',
                   '-c', 'user.email=azuresdk@microsoft.com',
                   'commit', '-m', title]
            logging.info('Command line: ' + ' '.join(cmd))
            subprocess.check_call(cmd, cwd=example_repo_path)

            # git push
            remote_uri = 'https://' + github_token + '@' + operation.sdk_examples_repository[len('https://'):]
            cmd = ['git', 'push', remote_uri, branch]
            # do not print this as it contains token
            # logging.info('Command line: ' + ' '.join(cmd))
            subprocess.check_call(cmd, cwd=example_repo_path)

            # create github pull request
            head = f'{operation.repository_owner}:{branch}'
            create_pull_request(operation, title, head)

            if operation.persist_data:
                # commit changes to database
                commit_database(release_name, sdk.language, release, changed_files)
    except subprocess.CalledProcessError as e:
        logging.error(f'Call error: {e}')
        aggregated_error.errors.append(e)
    finally:
        if clean_tmp_dir:
            shutil.rmtree(tmp_path, ignore_errors=True)


def commit_database(release_name: str, language: str, release: Release, changed_files: List[str]):
    # write to local database and commit to repository

    tmp_root_path = path.join(root_path, tmp_folder)
    database_path = path.join(tmp_root_path, database_folder)

    database_filename = 'examples.db'
    database = Database(path.join(database_path, database_filename))
    database_succeeded = database.new_release(
        release_name, language, release.tag, release.package, release.version, release.date, changed_files)
    if database_succeeded:
        # git add
        cmd = ['git', 'add', database_filename]
        logging.info('Command line: ' + ' '.join(cmd))
        subprocess.check_call(cmd, cwd=database_path)

        # git commit
        title = f'[Automation] Update database for {language}#{release.tag}'
        logging.info(f'git commit: {title}')
        cmd = ['git',
               '-c', 'user.name=azure-sdk',
               '-c', 'user.email=azuresdk@microsoft.com',
               'commit', '-m', title]
        logging.info('Command line: ' + ' '.join(cmd))
        subprocess.check_call(cmd, cwd=database_path)

        # git push
        remote_uri = 'https://' + github_token + '@' + automation_repo[len('https://'):]
        cmd = ['git', 'push', remote_uri, database_branch]
        # do not print this as it contains token
        # logging.info('Command line: ' + ' '.join(cmd))
        subprocess.check_call(cmd, cwd=database_path)


def process_sdk(operation: OperationConfiguration, sdk: SdkConfiguration, aggregated_error: AggregatedError):
    # process for sdk

    logging.info(f'Processing sdk: {sdk.name}')
    releases = []
    # since there is no ordering from GitHub, just get all releases (exclude draft=True), and hope paging is correct
    for page in itertools.count(start=1):
        request_uri = f'https://api.github.com/repos/{sdk.repository_owner}/{sdk.repository_name}/releases'
        releases_response = requests.get(request_uri,
                                         params={'per_page': 100, 'page': page},
                                         headers={'Authorization': f'token {github_token}'})
        if releases_response.status_code == 200:
            releases_response_json = releases_response.json()
            if len(releases_response_json) == 0:
                # no more result, we are done
                break
            for release in releases_response_json:
                if not release['draft']:
                    published_at = datetime.fromisoformat(release['published_at'].replace('Z', '+00:00'))
                    if operation.date_start < published_at < operation.date_end:
                        release_tag = release['tag_name']
                        if re.match(sdk.release_tag.regex_match, release_tag):
                            package = re.match(sdk.release_tag.package_regex_group, release_tag).group(1)
                            version = re.match(sdk.release_tag.version_regex_group, release_tag).group(1)
                            release = Release(release_tag, package, version, published_at)
                            releases.append(release)
                            logging.info(f'Found release tag: {release.tag}')
        else:
            logging.error(f'Request failed: {releases_response.status_code}\n{releases_response.json()}')
            try:
                releases_response.raise_for_status()
            except Exception as e:
                aggregated_error.errors.append(e)
            break

    for release in releases:
        process_release(operation, sdk, release, aggregated_error)


def process(command_line: CommandLineConfiguration, aggregated_error: AggregatedError):
    configuration = load_configuration(command_line)

    if command_line.merge_pr:
        merge_pull_requests(configuration.operation)

    # checkout azure-rest-api-specs repo
    tmp_root_path = path.join(root_path, tmp_folder)
    os.makedirs(tmp_root_path, exist_ok=True)
    spec_repo_path = path.join(tmp_root_path, tmp_spec_folder)
    spec_repo = 'https://github.com/Azure/azure-rest-api-specs'
    cmd = ['git', 'clone',
           '--quiet',
           '--depth', '1',
           spec_repo, spec_repo_path]
    logging.info(f'Checking out repository: {spec_repo}')
    logging.info('Command line: ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=tmp_root_path)

    # checkout database
    database_path = path.join(tmp_root_path, database_folder)
    cmd = ['git', 'clone',
           '--quiet',
           '--branch', database_branch,
           automation_repo, database_path]
    logging.info(f'Checking out repository: {automation_repo}, branch {database_branch}')
    logging.info('Command line: ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=tmp_root_path)

    for sdk_configuration in configuration.sdks:
        if not command_line.language or command_line.language == sdk_configuration.language:
            process_sdk(configuration.operation, sdk_configuration, aggregated_error)


def main():
    global root_path
    global github_token

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %X')

    script_path = path.abspath(path.dirname(sys.argv[0]))
    root_path = path.abspath(path.join(script_path, '..'))

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--build-id', type=str, required=True,
                        help='Build ID')
    parser.add_argument('--github-token', type=str, required=True,
                        help='GitHub token')
    parser.add_argument('--release-in-days', type=int, required=False, default=3,
                        help='Process SDK released within given days')
    parser.add_argument('--language', type=str, required=False,
                        help='Process SDK for specific language. Currently supports "java" and "go".')
    parser.add_argument('--persist-data', type=str, required=False, default='false',
                        help='Persist data about release and files to database')
    parser.add_argument('--merge-pull-request', type=str, required=False, default='false',
                        help='Merge GitHub pull request before new processing')
    args = parser.parse_args()

    github_token = args.github_token

    command_line_configuration = CommandLineConfiguration(args.build_id, args.release_in_days, args.language,
                                                          args.persist_data.lower() == 'true',
                                                          args.merge_pull_request.lower() == 'true')

    aggregated_error = AggregatedError([])
    process(command_line_configuration, aggregated_error)

    if aggregated_error.errors:
        raise RuntimeError(aggregated_error.errors)


if __name__ == '__main__':
    main()
