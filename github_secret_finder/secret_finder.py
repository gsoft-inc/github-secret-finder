from typing import Iterable
from analysis import PatchAnalyzer
from findings.finding import Finding
from github import GithubApiClient, GithubSearchClient, GithubApi
from findings import FindingsDatabase
from sqlitedict import SqliteDict
import logging


class SecretFinder(object):
    def __init__(self, tokens, db_file, blacklist_file, cache_only):
        self._cache_only = cache_only
        self._db_file = db_file
        self._api = GithubApi(GithubApiClient(tokens), GithubSearchClient(tokens), db_file, cache_only)
        self._patch_analyzer = PatchAnalyzer(blacklist_file)

    def __enter__(self):
        if not hasattr(self, '_commits_db') or self._commits_db is None:
            self._commits_db = SqliteDict(self._db_file, tablename="analyzed_commits", autocommit=True)

        if not hasattr(self, '_findings_db') or self._findings_db is None:
            self._findings_db = FindingsDatabase(self._db_file)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._commits_db.close()
        self._findings_db.close()

    def find_by_username(self, username) -> Iterable[Finding]:
        for qualifier in ["committer", "author"]:
            for r in self._find_by_query("%s:%s" % (qualifier, username)):
                yield r

    def find_by_name(self, name) -> Iterable[Finding]:
        for qualifier in ["committer-name", "author-name"]:
            for r in self._find_by_query("%s:\"%s\"" % (qualifier, name)):
                yield r

    def find_by_email(self, email) -> Iterable[Finding]:
        for qualifier in ["committer-email", "author-email"]:
            for r in self._find_by_query("%s:%s" % (qualifier, email)):
                yield r

    def find_by_organization(self, organization) -> Iterable[Finding]:
        logging.info("Organization: %s" % organization)
        return self._find_secrets(self._api.get_organization_commits(organization))

    def _find_by_query(self, query) -> Iterable[Finding]:
        logging.info("Query: %s" % query)
        return self._find_secrets(self._api.search_commits(query))

    def _find_secrets(self, commit_source) -> Iterable[Finding]:
        if self._cache_only:
            return self._find_secrets_from_cache(commit_source)
        else:
            return self._find_secrets_from_api(commit_source)

    def _find_secrets_from_cache(self, commit_source) -> Iterable[Finding]:
        commits = set(commit.id for commit in commit_source)
        return self._findings_db.get_findings(lambda x: x.commit.id in commits)

    def _find_secrets_from_api(self, commit_source) -> Iterable[Finding]:
        for commit in commit_source:
            if commit.id in self._commits_db:
                continue

            patch = self._api.get_commit_patch(commit.api_url)
            if not patch:
                continue

            logging.info(commit.html_url)

            for secret in self._patch_analyzer.find_secrets(patch):
                yield self._findings_db.create(commit, secret)

            self._commits_db[commit.id] = None


