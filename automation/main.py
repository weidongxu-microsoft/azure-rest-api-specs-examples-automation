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
from typing import List
import itertools
import requests
from database import Database

github_token: str
root_path: str = '.'

clean_tmp_dir: bool = True
tmp_folder: str = 'tmp'
tmp_spec_folder: str = 'spec'
tmp_example_folder: str = 'example'
tmp_sdk_folder: str = 'sdk'


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


@dataclasses.dataclass(eq=True, frozen=True)
class Release:
    tag: str
    package: str
    version: str
    date: datetime


def load_configuration(command_line: CommandLineConfiguration) -> Configuration:
    with open(path.join(root_path, 'automation/configuration.json'), 'r', encoding='utf-8') as f_in:
        config = json.load(f_in)

    now = datetime.now(timezone.utc)
    operation_configuration = OperationConfiguration(config['sdkExample']['repository'],
                                                     command_line.build_id,
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


def process_release(operation: OperationConfiguration, sdk: SdkConfiguration, release: Release):
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
        if path.isfile(output_json_path):
            with open(output_json_path, 'r', encoding='utf-8') as f_in:
                output = json.load(f_in)
                release_name = output['name']

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

            changed_files = [file.strip()[2:] for file in output_str.splitlines()]

            # git add
            cmd = ['git', 'add', '--all']
            logging.info('Command line: ' + ' '.join(cmd))
            subprocess.check_call(cmd, cwd=example_repo_path)

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
                   'commit', f'--message="{title}"']
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

            # write to database
            database_path = path.join(root_path, 'database', 'examples.db')
            database = Database(database_path)
            database_succeeded = database.new_release(
                release_name, sdk.language, release.tag, release.package, release.version, release.date, changed_files)
            if database_succeeded:
                # current branch
                cmd = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
                logging.info('Command line: ' + ' '.join(cmd))
                output = subprocess.check_output(cmd, cwd=root_path)
                current_branch = str(output, 'utf-8').strip()

                if not current_branch == 'HEAD':
                    # git add
                    cmd = ['git', 'add', database_path]
                    logging.info('Command line: ' + ' '.join(cmd))
                    subprocess.check_call(cmd, cwd=root_path)

                    # git commit
                    title = f'[Automation] Update database for {sdk.name}#{release_name}'
                    logging.info(f'git commit: {title}')
                    cmd = ['git',
                           '-c', 'user.name=azure-sdk',
                           '-c', 'user.email=azuresdk@microsoft.com',
                           'commit', f'--message="{title}"']
                    logging.info('Command line: ' + ' '.join(cmd))
                    subprocess.check_call(cmd, cwd=root_path)

                    # git push
                    remote_uri = f'https://{github_token}@' \
                                 'github.com/weidongxu-microsoft/azure-rest-api-specs-examples-automation'
                    cmd = ['git', 'push', remote_uri, current_branch]
                    # do not print this as it contains token
                    # logging.info('Command line: ' + ' '.join(cmd))
                    subprocess.check_call(cmd, cwd=root_path)

    except subprocess.CalledProcessError as error:
        logging.error(f'Call error: {error}')
    finally:
        if clean_tmp_dir:
            shutil.rmtree(tmp_path, ignore_errors=True)


def process_sdk(operation: OperationConfiguration, sdk: SdkConfiguration):
    # process for sdk

    # checkout azure-rest-api-specs repo
    tmp_root_path = path.join(root_path, tmp_folder)
    os.makedirs(tmp_root_path, exist_ok=True)
    spec_repo_path = path.join(tmp_root_path, tmp_spec_folder)
    spec_repo = 'https://github.com/Azure/azure-rest-api-specs'
    cmd = ['git', 'clone',
           '--quiet',
           '--depth', '1',
           spec_repo, spec_repo_path]
    logging.info(f'Checking out repository: spec_repo')
    logging.info('Command line: ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=tmp_root_path)

    logging.info(f'Processing sdk: {sdk.name}')
    releases = []
    # since there is no ordering from github, just get all releases (exclude draft=True), and hope paging is correct
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
            break

    for release in releases:
        process_release(operation, sdk, release)


def process(command_line: CommandLineConfiguration):
    configuration = load_configuration(command_line)
    for sdk_configuration in configuration.sdks:
        process_sdk(configuration.operation, sdk_configuration)


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
                        help='build ID')
    parser.add_argument('--github-token', type=str, required=True,
                        help='GitHub token')
    parser.add_argument('--release-in-days', type=int, required=False, default=3,
                        help='process SDK released within given days')
    args = parser.parse_args()

    github_token = args.github_token

    command_line_configuration = CommandLineConfiguration(args.build_id, args.release_in_days)

    process(command_line_configuration)


if __name__ == '__main__':
    main()
