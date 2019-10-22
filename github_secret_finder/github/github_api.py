from collections import Iterable
from sqlitedict import SqliteDict
from .models import GithubCommit, GithubRepository
from .github_api_client import GithubApiClient
from .github_search_client import GithubSearchClient
import hashlib


class GithubApi(object):
    _commits_table_prefix = "commits"
    _repos_table_prefix = "repos"

    def __init__(self, api_client: GithubApiClient, search_client: GithubSearchClient, db_file: str, cache_only: bool):
        self._cache_only = cache_only
        self._api_client = api_client
        self._db_file = db_file
        self._search_client = search_client

    def search_commits(self, query) -> 'Iterable[GithubCommit]':
        return self._get_commits(query, lambda: self._search_client.search_commits(query))

    def get_organization_commits(self, organization) -> 'Iterable[GithubCommit]':
        for repo in self.get_organization_repositories(organization):
            for commit in self._get_commits(repo.commits_url, lambda: self._api_client.get_repository_commits(repo.commits_url)):
                yield commit

    def get_commit_patch(self, url) -> str:
        return self._api_client.get_commit_patch(url)

    def get_organization_repositories(self, organization) -> 'Iterable[GithubRepository]':
        with self._get_db(self._repos_table_prefix, organization) as db:
            if not self._cache_only:
                for repo in self._api_client.get_repositories(organization):
                    db[repo.id] = repo
                db.commit()

            for repo in db.itervalues():
                yield repo

    def _get_commits(self, db_key, commit_source):
        if self._cache_only:
            return self._get_cached_commits(db_key)
        else:
            return self._get_new_and_cached_commits(db_key, commit_source)

    def _get_cached_commits(self, db_key):
        with self._get_db(self._commits_table_prefix, db_key) as db:
            for commit in db.itervalues():
                yield commit

    def _get_new_and_cached_commits(self, db_key, new_commit_source) -> 'Iterable[GithubCommit]':
        existing_commits = {}

        with self._get_db(self._commits_table_prefix, db_key) as db:
            for commit, x in db.iteritems():
                existing_commits[commit] = x

            for commit in new_commit_source():
                if commit.id in existing_commits:
                    break

                existing_commits[commit.id] = commit
                db[commit.id] = commit

            db.commit()

            for commit in existing_commits.values():
                yield commit

    def _get_db(self, prefix, key) -> SqliteDict:
        h = hashlib.sha1()
        h.update(key.encode("utf-8"))
        table_name = "%s_%s" % (prefix, h.hexdigest())
        return SqliteDict(self._db_file, tablename=table_name)



