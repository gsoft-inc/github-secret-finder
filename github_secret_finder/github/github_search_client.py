from typing import Iterable, TypeVar, Callable, Dict
from .models import BaseGithubCommit
from .github_rate_limited_requester import GithubRateLimitedRequester

TCommit = TypeVar('TCommit', bound=BaseGithubCommit)


class GithubSearchClient(object):
    def __init__(self, api_tokens):
        self._requester = GithubRateLimitedRequester(api_tokens)

    def search_commits(self, query, parser: Callable[[Dict], TCommit], max_results=-1) -> Iterable[TCommit]:
        for item in self._query_commits(query, max_results):
            yield parser(item)

    def _query_commits(self, query, max_results=-1):
        return self._requester.paginated_get("https://api.github.com/search/commits?sort=committer-date&order=desc&q=" + query.replace(" ", "+"), lambda x: x["items"], max_results)

    @staticmethod
    def _update_counts(counts_dict, key):
        if not key:
            return

        if key not in counts_dict:
            counts_dict[key] = 1
        else:
            counts_dict[key] += 1
