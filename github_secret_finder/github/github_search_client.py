from .models import GithubCommit
from .github_rate_limited_requester import GithubRateLimitedRequester
from collections import Iterable


class GithubSearchClient(object):
    def __init__(self, api_tokens):
        self._requester = GithubRateLimitedRequester(api_tokens)

    def search_commits(self, query) -> 'Iterable[GithubCommit]':
        for item in self._query_commits(query):
            yield GithubCommit(item["sha"], item["url"], item["html_url"])

    def search_commit_emails(self, username):
        emails = set()
        for query_type in ["author", "committer"]:
            for item in self._query_commits("%s:%s" % (query_type, username)):
                email = item["commit"][query_type]["email"]
                if email.endswith("@users.noreply.github.com") or email.endswith("github.com") or email in emails:
                    continue
                yield email

    def _get_commit_emails(self, item, selector):
        commit = item["commit"]
        yield commit["author"]["email"]
        yield commit["committer"]["email"]

    def _query_commits(self, query):
        return self._requester.paginated_get("https://api.github.com/search/commits?sort=committer-date&order=desc&q=" + query.replace(" ", "+"), lambda x: x["items"])