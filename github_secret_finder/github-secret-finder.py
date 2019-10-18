#!/usr/bin/env python3

import argparse
import uuid

from analysis import PatchAnalyzer
from github import GithubApiClient, CachedGithubSearchClient, GithubSearchClient
from sqlitedict import SqliteDict
import re


class GithubSecretFinder(object):
    def __init__(self, tokens, db_file, blacklist, verbose):
        self._verbose = verbose
        self._blacklist = blacklist
        self._db_file = db_file
        self._search = CachedGithubSearchClient(GithubSearchClient(tokens), db_file, "queries")
        self._api = GithubApiClient(tokens)

    def __enter__(self):
        if not hasattr(self, '_commits_db') or self._commits_db is None:
            self._commits_db = SqliteDict(self._db_file, tablename="analyzed_commits", autocommit=True)

        if not hasattr(self, '_findings_db') or self._findings_db is None:
            self._findings_db = SqliteDict(self._db_file, tablename="findings", autocommit=True)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._commits_db.close()
        self._findings_db.close()

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
        if self._verbose:
            print("Query: %s" % query)
        for commit, url in self._search.search_commits(query):
            if commit in self._commits_db:
                continue

            if self._verbose:
                print(url)
            patch = self._api.get_commit_patch(url)
            for secret in PatchAnalyzer().find_secrets(patch):
                if any(b for b in self._blacklist if re.match(b, secret.file_name)):
                    continue

                result = {"commit": commit, "secret": secret}
                yield result
                self._findings_db[str(uuid.uuid4())] = result

            self._commits_db[commit] = None


def create_list_from_args(file_name, single_value = None):
    if single_value:
        return [single_value]

    if file_name:
        with open(file_name, "r") as f:
            return [l.strip() for l in f.readlines() if l and not l.isspace()]

    return []

def print_result(result):
    commit = result["commit"]
    secret = result["secret"]

    s = ""
    if secret.verified:
        s += "[VERIFIED] "
    s += "%s - %s" % (commit, str(secret))
    print(s)


def main():
    parser = argparse.ArgumentParser(description='Github Secret Finder')
    parser.add_argument('--users', '-U', action='store', dest='users', help='File containing Github users to monitor.')
    parser.add_argument('--user', '-u', action="store", dest='user', help="Single Github user to monitor.")
    parser.add_argument('--emails', '-E', action='store', dest='emails', help='File containing email addresses to monitor.')
    parser.add_argument('--email', '-e', action="store", dest='email', help="Single email address to monitor.")
    parser.add_argument('--names', '-N', action='store', dest='names', help='File containing full names to monitor.')
    parser.add_argument('--name', '-n', action="store", dest='name', help="Single full name to monitor.")

    parser.add_argument('--tokens', '-t', action="store", dest='tokens', help="Github tokens separated by a comma (,)", required=True)

    parser.add_argument('--blacklist', '-b', action="append", dest='blacklist', nargs='+', default=[], help='Regexes to blacklist file names.')
    parser.add_argument('--blacklists', '-B', action='store', dest='blacklists', help='File containing regexes to blacklist file names.')

    parser.add_argument('--verbose', '-V', action="store_true", dest='verbose', default=False, help="Increases output verbosity.")
    args = parser.parse_args()

    emails = create_list_from_args(args.emails, args.email)
    names = create_list_from_args(args.names, args.name)
    users = create_list_from_args(args.users, args.user)

    tokens = [t.strip() for t in args.tokens.split(",")]

    blacklists = create_list_from_args(args.blacklists)
    blacklists.extend(b[0] for b in args.blacklist)

    database_file_name = "./github-secret-finder.sqlite"
    with GithubSecretFinder(tokens, database_file_name, blacklists, verbose=args.verbose) as finder:
        for user in users:
            for x in finder.find_by_username(user):
               print_result(x)

        for email in emails:
            for x in finder.find_by_email(email):
                print_result(x)

        for name in names:
            for x in finder.find_by_name(name):
                print_result(x)


if __name__ == "__main__":
    main()


