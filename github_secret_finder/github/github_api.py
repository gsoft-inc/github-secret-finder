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

    def get_organization_commits(self, organization, ignore_forks) -> Iterable[GithubCommit]:
        commit_ids = set()

        def get_compare_commits(compare_url, base, head):
            for c in self._api_client.get_compare_commits(compare_url, base, head):
                if c.id not in commit_ids:
                    yield c

        for repo in self.get_organization_repositories(organization):
            if repo.is_fork and ignore_forks:
                continue

            branches = list(self.get_repository_branches(repo))
            master = next((b for b in branches if b.name == "master"), None)
            if master:
                # There is a master branch. Fetch all commits from master and only compare the other branches.
                for c in self._get_commits(master.commits_url, lambda: self._api_client.get_branch_commits(master.commits_url)):
                    yield c
                for branch in [b for b in branches if b != master]:
                    for commit in self._get_commits(branch.commits_url, lambda: get_compare_commits(repo.compare_url, master.sha, branch.sha)):
                        commit_ids.add(commit.id)
                        yield commit
            else:
                # There is no master branch. Fetch all commits from all branches.
                for branch in branches:
                    for c in self._get_commits(branch.commits_url, lambda: self._api_client.get_branch_commits(branch.commits_url)):
                        if c.id not in commit_ids:
                            commit_ids.add(c.id)
                            yield c

    def get_commit_patch(self, url) -> str:
        return self._api_client.get_commit_patch(url)

    def get_organization_repositories(self, organization) -> Iterable[GithubRepository]:
        with self._get_db(self._repos_table_prefix, organization) as db:
            if not self._cache_only:
                for repo in self._api_client.get_organization_repositories(organization):
                    db[repo.id] = repo
                db.commit()

            for repo in db.itervalues():
                yield repo

    def get_repository_branches(self, repo: GithubRepository) -> Iterable[GithubBranch]:
        with self._get_db(self._branches_table_prefix, repo.branches_url) as db:
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
            for commit in db.itervalues():
                yield commit

            for commit in new_commit_source():
                if commit.id in db:
                    break
                db[commit.id] = commit
                yield commit

    def _get_db(self, prefix, key, auto_commit=False) -> SqliteDict:
        h = hashlib.sha1()
        h.update(key.encode("utf-8"))
        table_name = "%s_%s" % (prefix, h.hexdigest())
        return SqliteDict(self._db_file, tablename=table_name, autocommit=auto_commit)



