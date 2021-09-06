import os
import shutil
from os import path
import sys
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
import json
import re
import argparse
import logging
import dataclasses
from typing import List, Dict
import requests

github_token: str = os.environ.get('GITHUB_TOKEN')

clean_tmp_dir: bool = False

base_dir: str = '.'


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
    date_start: datetime = datetime.now(timezone.utc) - timedelta(days=10)
    date_end: datetime = datetime.now(timezone.utc)


@dataclasses.dataclass(eq=True, frozen=True)
class Configuration:
    operation: OperationConfiguration
    sdks: List[SdkConfiguration]


@dataclasses.dataclass(eq=True, frozen=True)
class Release:
    tag: str
    package: str
    version: str


def load_configuration(base_dir: str) -> Configuration:
    with open(path.join(base_dir, 'automation/configuration.json'), 'r', encoding='utf-8') as f_in:
        config = json.load(f_in)
    sdk_configurations = []
    for sdk_config in config['sdkConfigurations']:
        script = Script(sdk_config['script']['run'])
        release_tag = ReleaseTagConfiguration(sdk_config['releaseTag']['regexMatch'],
                                              sdk_config['releaseTag']['packageRegexGroup'],
                                              sdk_config['releaseTag']['versionRegexGroup'])
        sdk_configuration = SdkConfiguration(sdk_config['name'],
                                             sdk_config['repository'],
                                             release_tag, script)
        sdk_configurations.append(sdk_configuration)
    return Configuration(OperationConfiguration(config['sdkExample']['repository']), sdk_configurations)


def process_release(operation: OperationConfiguration, sdk: SdkConfiguration, release: Release):
    logging.info(f"Processing release: {release.tag}")

    tmp_root_path = path.join(base_dir, 'tmp')
    os.makedirs(tmp_root_path, exist_ok=True)
    tmp_path = tempfile.mkdtemp(prefix='tmp', dir=tmp_root_path)
    logging.info(f'Work directory: {tmp_path}')
    try:
        example_repo_path = path.join(tmp_path, 'example')
        sdk_repo_path = path.join(tmp_path, 'sdk')
        spec_repo_path = '/mnt/c/github/azure-rest-api-specs'

        cmd = ['git', 'clone',
               '--depth', '1',
               operation.sdk_examples_repository, example_repo_path]
        logging.info(f'Checking out repository: {operation.sdk_examples_repository}')
        logging.info('Command line: ' + ' '.join(cmd))
        subprocess.check_call(cmd, cwd=tmp_path)

        cmd = ['git', 'clone',
               '--depth', '1',
               '--branch', release.tag,
               sdk.repository, sdk_repo_path]
        logging.info(f'Checking out repository: {sdk.repository}')
        logging.info('Command line: ' + ' '.join(cmd))
        subprocess.check_call(cmd, cwd=tmp_path)

        input_json_path = path.join(tmp_path, 'input.json')
        output_json_path = path.join(tmp_path, 'output.json')
        with open(input_json_path, 'w', encoding='utf-8') as f_out:
            input_json = {
                "specsPath": spec_repo_path,
                "sdkExamplesPath": example_repo_path,
                "sdkPath": sdk_repo_path,
                "tempPath": tmp_path,
                "release": {
                    "tag": release.tag,
                    "package": release.package,
                    "version": release.version
                }
            }
            logging.info(f'Input JSON for worker: {input_json}')
            json.dump(input_json, f_out, indent=2)

        logging.info(f'Running worker: {sdk.script.run}')
        subprocess.check_call([sdk.script.run, input_json_path, output_json_path], cwd=base_dir)
    finally:
        if clean_tmp_dir:
            shutil.rmtree(tmp_path, ignore_errors=True)


def process_sdk(operation: OperationConfiguration, sdk: SdkConfiguration):
    logging.info(f"Processing sdk: {sdk.name}")

    releases = []
    page = 1
    while True:
        request_uri = f'https://api.github.com/repos/{sdk.repository_owner}/{sdk.repository_name}' \
                      f'/releases?per_page=100&page={page}'
        releases_response = requests.get(request_uri, headers={'Authorization': f'token {github_token}'})
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
                            release = Release(release_tag, package, version)
                            releases.append(release)
                            logging.info(f'Found release tag: {release.tag}')
        else:
            logging.error(f'Request failed: {request_uri}')
            break
        page += 1

    for release in releases:
        process_release(operation, sdk, release)


def process():
    configuration = load_configuration(base_dir)
    for sdk_configuration in configuration.sdks:
        process_sdk(configuration.operation, sdk_configuration)


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %X')
    global base_dir
    base_dir = path.abspath(path.join(path.abspath(os.path.dirname(sys.argv[0])), '..'))

    parser = argparse.ArgumentParser(description='')
    args = parser.parse_args()

    process()


if __name__ == '__main__':
    main()
