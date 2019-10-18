from .github_rate_limited_requester import GithubRateLimitedRequester
import json
import os


class GithubSearchClient(object):
    _search_history_file_name = "data/search-history.json"

    def __init__(self, api_tokens):
        self._requester = GithubRateLimitedRequester(api_tokens)
        self._load_history()

    def search_commits(self, query):
        new_urls = []
        if query in self._history:
            previous_urls = self._history[query]
        else:
            previous_urls = []
            self._history[query] = previous_urls

        for item in self._requester.paginated_get("https://api.github.com/search/commits?sort=committer-date&order=desc&q=" + query.replace(" ", "+")):
            url = item["commit"]["url"].replace("/git/commits", "/commits")
            if url in previous_urls:
                break
            new_urls.append(url)
            yield url

        if len(new_urls) > 0:
            previous_urls.extend(new_urls)
            self._save_history()

        for url in previous_urls:
            yield url

    def _load_history(self):
        self._history = {}
        if os.path.isfile(self._search_history_file_name):
            with open(self._search_history_file_name, "r") as f:
                self._history = json.load(f)

    def _save_history(self):
        tmp_file = self._search_history_file_name + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(self._history, f, indent=4)
        os.replace(tmp_file, self._search_history_file_name)

