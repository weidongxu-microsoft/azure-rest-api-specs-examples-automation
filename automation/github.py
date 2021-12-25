import requests
import logging
from typing import List, Dict


class GitHubRepository:
    api_host: str = '{self.api_host}'
    owner: str
    name: str
    token: str

    def __init__(self, owner: str, name: str, token):
        self.owner = owner
        self.name = name
        self.token = token

    def create_pull_request(self, title: str, head: str) -> int:
        logging.info(f'Create pull request: {head}')

        request_uri = f'{self.api_host}/repos/{self.owner}/{self.name}/pulls'
        request_body = {
            'title': title,
            'head': head,
            'base': 'main'
        }
        pull_request_response = requests.post(request_uri,
                                              json=request_body,
                                              headers={'Authorization': f'token {self.token}'})
        if pull_request_response.status_code == 201:
            logging.info('Pull request created')
            return pull_request_response.json()['number']
        else:
            logging.error(f'Request failed: {pull_request_response.status_code}\n{pull_request_response.json()}')
            pull_request_response.raise_for_status()

    def list_pull_requests(self) -> List[Dict]:
        logging.info(f'List pull requests')

        request_uri = f'{self.api_host}/repos/{self.owner}/{self.name}/pulls?per_page=100'
        pull_request_response = requests.get(request_uri,
                                             headers={'Authorization': f'token {self.token}'})
        if pull_request_response.status_code == 200:
            logging.info('Pull request created')
            return pull_request_response.json()
        else:
            logging.error(f'Request failed: {pull_request_response.status_code}\n{pull_request_response.json()}')
            return []

    def merge_pull_request(self, pull_request: Dict):
        title = pull_request['title']
        logging.info(f'Merge pull request: {title}')

        pull_number = int(pull_request['number'])

        request_uri = f'{self.api_host}/repos/{self.owner}/{self.name}/pulls/{pull_number}/merge'
        request_body = {
            'commit_title': title,
            'merge_method': 'squash'
        }
        pull_request_response = requests.put(request_uri,
                                             json=request_body,
                                             headers={'Authorization': f'token {self.token}'})
        if pull_request_response.status_code == 200:
            logging.info('Pull request merged')
        else:
            logging.error(f'Request failed: {pull_request_response.status_code}\n{pull_request_response.json()}')

    def list_releases(self, page: int, per_page: int) -> List[Dict]:
        request_uri = f'{self.api_host}/repos/{self.owner}/{self.name}/releases'
        releases_response = requests.get(request_uri,
                                         params={'per_page': per_page, 'page': page},
                                         headers={'Authorization': f'token {self.token}'})
        if releases_response.status_code == 200:
            return releases_response.json()
        else:
            logging.error(f'Request failed: {releases_response.status_code}\n{releases_response.json()}')
            releases_response.raise_for_status()
