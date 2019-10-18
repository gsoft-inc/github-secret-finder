from .github_rate_limited_requester import GithubRateLimitedRequester


class GithubSearchClient(object):
    def __init__(self, api_tokens):
        self._requester = GithubRateLimitedRequester(api_tokens)

    def search_commits(self, query):
        for item in self._requester.paginated_get("https://api.github.com/search/commits?sort=committer-date&order=desc&q=" + query.replace(" ", "+")):
            url = item["commit"]["url"].replace("/git/commits", "/commits")
            commit_id = item["sha"]

            yield commit_id, url

