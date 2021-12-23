import requests
import logging
from typing import List, Dict


class GitHubRepository:
    owner: str
    name: str
    token: str

    def __init__(self, owner: str, name: str, token):
        self.owner = owner
        self.name = name
        self.token = token

    def create_pull_request(self, title: str, head: str):
        logging.info(f'Create pull request: {head}')

        request_uri = f'https://api.github.com/repos/{self.owner}/{self.name}/pulls'
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
        else:
            logging.error(f'Request failed: {pull_request_response.status_code}\n{pull_request_response.json()}')

    def list_pull_requests(self) -> List[Dict]:
        logging.info(f'List pull requests')

        request_uri = f'https://api.github.com/repos/{self.owner}/{self.name}/pulls?per_page=100'
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

        pull_number = pull_request['number']

        request_uri = f'https://api.github.com/repos/{self.owner}/{self.name}/pulls/{pull_number}/merge'
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
