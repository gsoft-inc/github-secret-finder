from typing import Optional, Union, Iterable
from .models import GithubRepository, GithubCommit, GithubUser, GithubBranch
from .github_rate_limited_requester import GithubRateLimitedRequester


class GithubApiClient(object):
    def __init__(self, api_tokens):
        self._requester = GithubRateLimitedRequester(api_tokens)

    def get_commit_patch(self, url) -> Optional[str]:
        content = ""
        response = self._requester.get(url)
        if not response:
            return None

        json_response = response.json()

        if "files" in json_response:
            for f in json_response["files"]:
                if "patch" not in f:
                    continue

                filename = f["filename"]
                status = f["status"]

                prefix = ""
                if status == "renamed":
                    prefix += "--- %s\n" % f["previous_filename"]
                else:
                    prefix += "--- %s\n" % filename
                prefix += "+++ %s\n" % filename
                content += prefix + f["patch"] + "\n"

        return content

    def get_organization_repositories(self, organization) -> Iterable[GithubRepository]:
        for repo in self._requester.paginated_get("https://api.github.com/orgs/%s/repos" % organization, lambda x: x):
            if repo["fork"]:
                response = self._requester.get(repo["url"])
                if response:
                    repo = response.json()
            yield GithubRepository.from_json(repo)


    def get_repository_branches(self, repo: GithubRepository) -> Iterable[GithubBranch]:
        for item in self._requester.paginated_get(repo.get_branches_url(), lambda x: x):
            yield GithubBranch.from_json(item)

    def get_branch_commits(self, repo: GithubRepository, branch: GithubBranch, since_commit: GithubCommit = None) -> Iterable[GithubCommit]:
        since = None
        if since_commit:
            since = since_commit.date

        for item in self._requester.paginated_get(branch.get_commits_url(repo, since), lambda x: x, reverse=True):
            commit = GithubCommit.from_json(item)
            if since_commit and since_commit.sha == commit.sha:
                continue
            yield commit

    def get_compare_commits(self, repo: GithubRepository, base: GithubBranch, head: GithubBranch, compare_with_parent=False) -> Iterable[GithubCommit]:
        response = self._requester.get(repo.get_compare_url(base, head, compare_with_parent))
        if not response:
            raise StopIteration()
        json_response = response.json()

        # TODO Do something if there are more than 250 commits.
        for commit in json_response["commits"][::-1]:
            yield GithubCommit.from_json(commit)

    def get_repository_contributors(self, contributors_url) -> Iterable[Union[GithubUser, int]]:
        for contributor in self._requester.paginated_get(contributors_url, lambda x: x):
            response = self._requester.get(contributor["url"])
            if response is None:
                continue
            json_response = response.json()
            yield GithubUser.from_json(json_response), contributor["contributions"]
