from .models import GithubCommit
from .github_rate_limited_requester import GithubRateLimitedRequester
from collections import Iterable


class GithubSearchClient(object):
    def __init__(self, api_tokens):
        self._requester = GithubRateLimitedRequester(api_tokens)

    def search_commits(self, query) -> 'Iterable[GithubCommit]':
        for item in self._requester.paginated_get("https://api.github.com/search/commits?sort=committer-date&order=desc&q=" + query.replace(" ", "+"), lambda x: x["items"]):
            yield GithubCommit(item["sha"], item["url"], item["html_url"])
