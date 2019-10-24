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
            yield GithubRepository(repo["id"],
                                   repo["full_name"],
                                   repo["commits_url"].replace("{/sha}", "") + "?per_page=100",
                                   repo["branches_url"].replace("{/branch}", "") + "?per_page=100",
                                   repo["contributors_url"],
                                   repo["fork"])

    def get_repository_branches(self, repo: GithubRepository) -> Iterable[GithubBranch]:
        for item in self._requester.paginated_get(repo.branches_url, lambda x: x):
            sha = item["commit"]["sha"]
            yield GithubBranch(item["name"], sha, "%s&sha=%s" % (repo.commits_url, sha))

    def get_branch_commits(self, commits_url) -> Iterable[GithubCommit]:
        for item in self._requester.paginated_get(commits_url, lambda x: x):
            yield GithubCommit(item["sha"], item["url"], item["html_url"])

    def get_repository_contributors(self, contributors_url) -> Iterable[Union[GithubUser, int]]:
        for contributor in self._requester.paginated_get(contributors_url, lambda x: x):
            response = self._requester.get(contributor["url"])
            if response is None:
                continue
            json_response = response.json()
            yield GithubUser(json_response["login"], json_response["name"], json_response["url"], json_response["repos_url"]), contributor["contributions"]
