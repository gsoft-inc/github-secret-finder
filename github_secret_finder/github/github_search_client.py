from .models import GithubCommit
from .github_rate_limited_requester import GithubRateLimitedRequester
from collections import Iterable


class GithubSearchClient(object):
    def __init__(self, api_tokens):
        self._requester = GithubRateLimitedRequester(api_tokens)

    def search_commits(self, query) -> 'Iterable[GithubCommit]':
        for item in self._query_commits(query):
            yield GithubCommit(item["sha"], item["url"], item["html_url"])

    def search_commit_emails_by_username(self, username):
        return self._search_commit_emails(username, "")

    def search_commit_emails_by_full_name(self, name):
        # If the query returns more than 5000 results, assume that it's too generic and don't return anything.
        return self._search_commit_emails(name, "-name", 5000)

    def _search_commit_emails(self, value, query_suffix, max_results=-1):
        emails = {}
        for query_type in ["author", "committer"]:
            for item in self._query_commits("%s%s:\"%s\"" % (query_type, query_suffix, value), max_results):
                email = item["commit"][query_type]["email"].lower()
                if "@" not in email or email.endswith("@users.noreply.github.com") or email.endswith("github.com"):
                    continue

                if email not in emails:
                    emails[email] = 1
                else:
                    emails[email] += 1
        return emails

    def _query_commits(self, query, max_results=-1):
        return self._requester.paginated_get("https://api.github.com/search/commits?sort=committer-date&order=desc&q=" + query.replace(" ", "+"), lambda x: x["items"], max_results)