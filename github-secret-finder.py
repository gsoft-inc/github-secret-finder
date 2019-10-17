import argparse

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
        tmp_file = self._analyzed_commits_file_name + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(self._analyzed_commits, f, indent=4)
        os.replace(tmp_file, self._analyzed_commits_file_name)

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


def handle(f, x):
    commit_url, line, details = x
    print(commit_url, line, details)
    f.write("%s - %s - %s\n" % (commit_url, line.encode("utf-8"), json.dumps(details)))


def create_list_from_args(file_name, single_value):
    if single_value:
        return [single_value]

    if file_name:
        with open(file_name, "r") as f:
            return [l.strip() for l in f.readlines()]

    return []


def main():
    parser = argparse.ArgumentParser(description='Github Secret Finder')
    parser.add_argument('--users', '-U', action='store', dest='users', help='File containing Github users to monitor.')
    parser.add_argument('--user', '-u', action="store", dest='user', help="Single Github user to monitor.")
    parser.add_argument('--emails', '-E', action='store', dest='emails', help='File containing email addresses to monitor.')
    parser.add_argument('--email', '-e', action="store", dest='email', help="Single email address to monitor.")
    parser.add_argument('--names', '-N', action='store', dest='names', help='File containing full names to monitor.')
    parser.add_argument('--name', '-n', action="store", dest='name', help="Single full name to monitor.")

    parser.add_argument('--tokens', '-t', action="store", dest='tokens', help="Github tokens separated by a comma (,)", required=True)
    parser.add_argument('--filename-blacklist', '-fb', action="store", dest='filename-blacklist', help='Regex to blacklist file names.')
    args = parser.parse_args()

    finder = GithubSecretFinder(args.tokens.split(","))

    emails = create_list_from_args(args.emails, args.email)
    names = create_list_from_args(args.names, args.name)
    users = create_list_from_args(args.users, args.user)

    with open("data/findings.txt", "a") as f:
        for user in users:
            for x in finder.find_by_username(user):
                handle(f, x)

        for email in emails:
            for x in finder.find_by_email(email):
                handle(f, x)

        for name in names:
            for x in finder.find_by_name(name):
                handle(f, x)


if __name__ == "__main__":
    main()


