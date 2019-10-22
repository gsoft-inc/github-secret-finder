import operator
import requests
import time
from datetime import datetime
from requests import RequestException
from .github_token_rate_limit_information import GithubTokenRateLimitInformation
import logging


class GithubRateLimitedRequester(object):
    _max_retries = 5
    _throttle_messages = ["API rate limit exceeded", "abuse detection mechanism"]

    def __init__(self, tokens):
        self._token_infos = []
        for t in tokens:
            self._token_infos.append(GithubTokenRateLimitInformation(t))

    def get(self, url):
        retry = 1
        while True:
            status_codes = []
            for token_info in sorted(self._token_infos, key=operator.attrgetter("remaining"), reverse=True):
                if token_info.remaining == 0 and token_info.reset_time > datetime.utcnow():
                    continue

                try:
                    response = requests.get(url, headers={'Accept': 'application/vnd.github.cloak-preview', 'Authorization': "token " + token_info.token})
                    status_codes.append(response.status_code)
                    token_info.update(response)

                    if response.status_code == 200:
                        return response
                except RequestException:
                    continue

            if retry >= self._max_retries:
                logging.error("Could not get %s. Skipping." % url)
                return None
            if len(status_codes) >= 1 and all([s for s in status_codes if s == 403]):
                # Assume the calls failed because of a timeout.
                sleep_time = (min([t.reset_time for t in self._token_infos]) - datetime.utcnow()).total_seconds() + 1
                logging.warning("Rate limiting error. Sleeping %d seconds." % sleep_time)
            else:
                sleep_time = retry * 5
                logging.error("Unhandled error. Retrying in %d seconds." % sleep_time)

            retry += 1
            if sleep_time > 0:
                time.sleep(sleep_time)

    def paginated_get(self, url, items_selector):
        while True:
            response = self.get(url)
            if not response:
                break

            for item in items_selector(response.json()):
                yield item

            if "next" in response.links:
                url = response.links["next"]["url"]
            else:
                break
