from collections import Iterable
from typing import Optional
from .models import GithubRepository, GithubCommit
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

    def get_repositories(self, organization) -> 'Optional[Iterable[GithubRepository]]':
        for repo in self._requester.paginated_get("https://api.github.com/orgs/%s/repos" % organization, lambda x: x):
            yield GithubRepository(repo["id"], repo["full_name"], repo["commits_url"].replace("{/sha}", ""))

    def get_repository_commits(self, commits_url) -> 'Iterable[GithubCommit]':
        for item in self._requester.paginated_get(commits_url, lambda x: x):
            yield GithubCommit(item["sha"], item["url"], item["html_url"])


