from typing import Iterable
from sqlitedict import SqliteDict
from .models import GithubCommit, GithubRepository, GithubBranch
from .github_api_client import GithubApiClient
from .github_search_client import GithubSearchClient
import hashlib


class GithubApi(object):
    _commits_table_prefix = "commits"
    _repos_table_prefix = "repos"
    _branches_table_prefix = "branches"

    def __init__(self, api_client: GithubApiClient, search_client: GithubSearchClient, db_file: str, cache_only: bool):
        self._cache_only = cache_only
        self._api_client = api_client
        self._db_file = db_file
        self._search_client = search_client

    def search_commits(self, query) -> Iterable[GithubCommit]:
        return self._get_commits(query, lambda: self._search_client.search_commits(query))

    def get_organization_commits(self, organization) -> Iterable[GithubCommit]:
        for repo in self.get_organization_repositories(organization):
            branches = list(self.get_repository_branches(repo))
            default_branch = [b for b in branches if b.name == repo.default_branch][0]

            if not repo.is_fork or repo.parent is None:
                # Return commits from the default branch.
                for commit in self._get_commits(self._get_branch_cache_key(repo, default_branch), lambda since_commit: self._api_client.get_branch_commits(repo, default_branch, since_commit)):
                    yield commit

                parent_branches = branches
            else:
                parent_branches = list(self.get_repository_branches(repo.parent))

            # For each branch, return commits that are not in the default branch.
            for branch in branches:
                if repo.is_fork:
                    base_branch = next((b for b in parent_branches if b.name == branch.name), default_branch)  # Compare with the same branch if it exists. Otherwise, compare with the default branch.
                else:
                    if branch == default_branch:
                        continue  # The commits for this branch were already returned.
                    base_branch = default_branch

                cache_key = self._get_branch_cache_key(repo, branch)
                for commit in self._get_commits(cache_key, lambda x: (c for c in self._api_client.get_compare_commits(repo, base_branch, branch, compare_with_parent=repo.is_fork))):
                    yield commit

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

    def _get_commits(self, db_key, commit_source) -> Iterable[GithubCommit]:
        if self._cache_only:
            return self._get_cached_commits(db_key)
        else:
            return self._get_new_and_cached_commits(db_key, commit_source)

    def _get_cached_commits(self, db_key):
        with self._get_db(self._commits_table_prefix, db_key) as db:
            for commit in db.itervalues():
                yield commit

    def _get_new_and_cached_commits(self, db_key, new_commit_source) -> Iterable[GithubCommit]:
        with self._get_db(self._commits_table_prefix, db_key, auto_commit=True) as db:
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


