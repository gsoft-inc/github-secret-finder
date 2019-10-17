from github_api_client import GithubApiClient
from github_search_client import GithubSearchClient
import json
import os

from patch_secret_finder import PatchSecretFinder


class GithubSecretFinder(object):
    _analyzed_commits_file_name = "data/analyzed-commits.json"

    def __init__(self, tokens):
        self._search = GithubSearchClient(tokens)
        self._api = GithubApiClient(tokens)
        self._load_analyzed_commits()

    def _load_analyzed_commits(self):
        self._analyzed_commits = []
        if os.path.isfile(self._analyzed_commits_file_name):
            with open(self._analyzed_commits_file_name, "r") as f:
                self._analyzed_commits = json.load(f)

    def _save_analyzed_commits(self):
        with open(self._analyzed_commits_file_name, "w") as f:
            json.dump(self._analyzed_commits, f, indent=4)

    def find_by_username(self, username):
        for qualifier in ["committer", "author"]:
            for r in self._find("%s:%s" % (qualifier, username)):
                yield r

    def find_by_name(self, name):
        for qualifier in ["committer-name", "author-name"]:
            for r in self._find("%s:\"%s\"" % (qualifier, name)):
                yield r

    def find_by_email(self, email):
        for qualifier in ["committer-email", "author-email"]:
            for r in self._find("%s:%s" % (qualifier, email)):
                yield r

    def _find(self, query):
        print("Query: %s" % query)
        for url in self._search.search_commits(query):
            commit_id = url[url.rfind("/") + 1:]
            if commit_id in self._analyzed_commits:
                continue

            print(url)
            patch = self._api.get_commit_patch(url)
            for line, details in PatchSecretFinder().find_secrets(patch):
                yield url, line, details

            self._analyzed_commits.append(commit_id)
            self._save_analyzed_commits()


finder = GithubSecretFinder(["TODO TOKENS"])

def handle(x):
    commit_url, line, details = x
    print(commit_url, line, details)
    f.write("%s - %s - %s\n" % (commit_url, line.encode("utf-8"), json.dumps(details)))


emails = ["TODO EMAIL"]
names = ["TODO NAME"]
with open("data/users.txt", "r") as f:
    usernames = [l.strip() for l in f.readlines()]

with open("data/findings.txt", "a") as f:
    for username in usernames:
        for x in finder.find_by_username(username):
            handle(x)

    for email in emails:
        for x in finder.find_by_email(email):
            handle(x)

    for name in names:
        for x in finder.find_by_name(name):
            handle(x)
