import hashlib
from typing import Iterable, Union

from sqlitedict import SqliteDict

from .github_api_client import GithubApiClient
from .github_commit_information_fetcher import GithubCommitInformationFetcher
from .github_search_client import GithubSearchClient
from .models import GithubCommit, GithubRepository, GithubBranch, GithubCommitWithUsers, GithubUser
from ..util.legacy_unpickler import legacy_decode


class GithubApi(object):
    _commits_table_prefix = "commits"
    _commit_users_table_prefix = "commit_users"
    _repos_table_prefix = "repos"
    _contributors_table_prefix = "contributors"
    _branches_table_prefix = "branches"
    _users_table = "users"

    def __init__(self, api_client: GithubApiClient, search_client: GithubSearchClient, db_file: str, cache_only: bool):
        self._cache_only = cache_only
        self._api_client = api_client
        self._db_file = db_file
        self._search_client = search_client
        self._commit_fetcher = GithubCommitInformationFetcher(api_client, search_client, self.get_repository_branches, db_file, self._commits_table_prefix, cache_only, GithubCommit.from_json)
        self._commits_with_users_fetcher = GithubCommitInformationFetcher(api_client, search_client, self.get_repository_branches, db_file, self._commit_users_table_prefix, cache_only, GithubCommitWithUsers.from_json)

    def search_commits(self, query) -> Iterable[GithubCommit]:
        return self._commit_fetcher.search_commits(query)

    def search_users_from_commits(self, query) -> Iterable[GithubCommitWithUsers]:
        # Assume that if a query returns more than 3000 results, it's too generic.
        return self._commits_with_users_fetcher.search_commits(query, max_results=3000)

    def get_organization_commits(self, organization) -> Iterable[GithubCommit]:
        for repo in self.get_organization_repositories(organization):
            for commit in self._commit_fetcher.get_repository_commits(repo):
                yield commit

    def get_repository_commit_users(self, repo: GithubRepository) -> Iterable[GithubCommitWithUsers]:
        return self._commits_with_users_fetcher.get_repository_commits(repo)

    def get_commit_patch(self, url) -> str:
        return self._api_client.get_commit_patch(url)

    def get_organization_repositories(self, organization) -> Iterable[GithubRepository]:
        with self._get_db(self._repos_table_prefix, organization) as db:
            if not self._cache_only:
                for repo in self._api_client.get_organization_repositories(organization):
                    db[repo.name] = repo
                db.commit()

            for repo in db.itervalues():
                yield repo

    def get_repository_branches(self, repo: GithubRepository) -> Iterable[GithubBranch]:
        with self._get_db(self._branches_table_prefix, repo.get_branches_url()) as db:
            if not self._cache_only:
                for branch in self._api_client.get_repository_branches(repo):
                    db[branch.name] = branch
                db.commit()

            for repo in db.itervalues():
                yield repo

    def get_repository_contributors(self, contributors_url) -> Iterable[Union[GithubUser, int]]:
        with self._get_db(self._contributors_table_prefix, contributors_url) as db:
            if not self._cache_only:
                for login, count in self._api_client.get_repository_contributors(contributors_url):
                    db[login] = count
                db.commit()

                with SqliteDict(self._db_file, tablename=self._users_table, autocommit=True, decode=legacy_decode) as users_db:
                    for login, count in db.iteritems():
                        if login in users_db:
                            yield users_db[login], count
                        elif not self._cache_only:
                            user = self._api_client.get_user(login)
                            if user:
                                users_db[login] = user
                                yield user, count

    def _get_db(self, prefix, key, auto_commit=False) -> SqliteDict:
        h = hashlib.sha1()
        h.update(key.encode("utf-8"))
        table_name = "%s_%s" % (prefix, h.hexdigest())
        return SqliteDict(self._db_file, tablename=table_name, autocommit=auto_commit, decode=legacy_decode)
