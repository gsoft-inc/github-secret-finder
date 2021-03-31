import hashlib
from typing import Iterable, TypeVar, Generic, Callable, Dict

from sqlitedict import SqliteDict

from .github_api_client import GithubApiClient
from .github_search_client import GithubSearchClient
from .models import GithubRepository, GithubBranch, BaseGithubCommit

T = TypeVar('T', bound=BaseGithubCommit)


class GithubCommitInformationFetcher(Generic[T]):
    def __init__(self, api_client: GithubApiClient, search_client: GithubSearchClient, get_repository_branches: Callable[[GithubRepository], Iterable[GithubBranch]], db_file: str, table_prefix: str, cache_only: bool, json_parser: Callable[[Dict], T]):
        self._get_repository_branches = get_repository_branches
        self._db_file = db_file
        self._table_prefix = table_prefix
        self._cache_only = cache_only
        self._json_parser = json_parser
        self._search_client = search_client
        self._api_client = api_client

    def search_commits(self, query, max_results=-1) -> Iterable[T]:
        return self._get_commits(query, lambda x: self._search_client.search_commits(query, self._json_parser, max_results))

    def get_repository_commits(self, repo: GithubRepository) -> Iterable[T]:
        branches = list(self._get_repository_branches(repo))
        default_branch = [b for b in branches if b.name == repo.default_branch][0]

        if not repo.is_fork or repo.parent is None:
            # Return commits from the default branch.
            for commit in self._get_commits(self._get_branch_cache_key(repo, default_branch), lambda since_commit: self._api_client.get_branch_commits(repo, default_branch, self._json_parser, since_commit)):
                yield commit

            parent_branches = branches
        else:
            parent_branches = list(self._get_repository_branches(repo.parent))

        # For each branch, return commits that are not in the default branch.
        for branch in branches:
            if repo.is_fork:
                base_branch = next((b for b in parent_branches if b.name == branch.name), default_branch)  # Compare with the same branch if it exists. Otherwise, compare with the default branch.
            else:
                if branch == default_branch:
                    continue  # The commits for this branch were already returned.
                base_branch = default_branch

            cache_key = self._get_branch_cache_key(repo, branch)
            for commit in self._get_commits(cache_key, lambda x: self._api_client.get_compare_commits(repo, base_branch, branch, self._json_parser, compare_with_parent=repo.is_fork)):
                yield commit

    def _get_commits(self, db_key, commit_source) -> Iterable[T]:
        if self._cache_only:
            return self._get_cached_commits(db_key)
        else:
            return self._get_new_and_cached_commits(db_key, commit_source)

    def _get_cached_commits(self, db_key) -> Iterable[T]:
        with self._get_db(self._table_prefix, db_key) as db:
            for commit in db.itervalues():
                yield commit

    def _get_new_and_cached_commits(self, db_key, new_commit_source) -> Iterable[T]:
        with self._get_db(self._table_prefix, db_key, auto_commit=True) as db:
            since_commit = None

            for commit in db.itervalues():
                since_commit = commit
                yield commit

            for commit in new_commit_source(since_commit):
                if commit.sha in db:
                    break
                db[commit.sha] = commit
                yield commit

    def _get_db(self, prefix, key, auto_commit=False) -> SqliteDict:
        h = hashlib.sha1()
        h.update(key.encode("utf-8"))
        table_name = "%s_%s" % (prefix, h.hexdigest())
        return SqliteDict(self._db_file, tablename=table_name, autocommit=auto_commit)

    @staticmethod
    def _get_branch_cache_key(repo: GithubRepository, branch: GithubBranch):
        return repo.name + "/" + branch.name
