#!/usr/bin/env python3

import argparse
from analysis import PatchAnalyzer
from github import GithubApiClient, CachedGithubSearchClient, GithubSearchClient
from sqlitedict import SqliteDict


class GithubSecretFinder(object):
    def __init__(self, tokens, db_file):
        self._db_file = db_file
        self._search = CachedGithubSearchClient(GithubSearchClient(tokens), db_file, "queries")
        self._api = GithubApiClient(tokens)

    def __enter__(self):
        if not hasattr(self, '_db') or self._db is None:
            self._db = SqliteDict(self._db_file, tablename="analyzed_commits", autocommit=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._db.close()

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
        for commit, url in self._search.search_commits(query):
            if commit in self._db:
                continue

            print(url)
            patch = self._api.get_commit_patch(url)
            for line, details in PatchAnalyzer().find_secrets(patch):
                yield url, line, details

            self._db[commit] = None


def handle(findings_db, x):
    commit_url, line, details = x
    print(commit_url, line, details)
    findings_db[commit_url] = (line, details)


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

    emails = create_list_from_args(args.emails, args.email)
    names = create_list_from_args(args.names, args.name)
    users = create_list_from_args(args.users, args.user)

    tokens = [t.strip() for t in args.tokens.split(",")]

    database_file_name = "./github-secret-finder.sqlite"
    with GithubSecretFinder(tokens, database_file_name) as finder:
        with SqliteDict(database_file_name, tablename="findings", autocommit=True) as findings_db:
            for user in users:
                for x in finder.find_by_username(user):
                    handle(findings_db, x)

            for email in emails:
                for x in finder.find_by_email(email):
                    handle(findings_db, x)

            for name in names:
                for x in finder.find_by_name(name):
                    handle(findings_db, x)


if __name__ == "__main__":
    main()


