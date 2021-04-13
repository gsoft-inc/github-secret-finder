import logging
import operator
import time
import urllib.parse as urlparse
from datetime import datetime
from urllib.parse import urlencode

import requests
from requests import RequestException

from .github_token_rate_limit_information import GithubTokenRateLimitInformation


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

                    if response.status_code == 404:
                        return None
                except RequestException:
                    continue

            if retry >= self._max_retries:
                logging.error("Could not get %s. Skipping." % url)
                return None
            if all(t.remaining == 0 for t in self._token_infos):
                # Assume the calls failed because of a timeout.
                sleep_time = (min([t.reset_time for t in self._token_infos]) - datetime.utcnow()).total_seconds() + 1
                logging.warning("Rate limit reached. Sleeping %d seconds." % sleep_time)
            else:
                sleep_time = retry * 5
                logging.error("Unhandled error. Retrying in %d seconds." % sleep_time)

            retry += 1
            if sleep_time > 0:
                time.sleep(sleep_time)

    def paginated_get(self, url, items_selector, max_results=-1, reverse=False):
        url = self._add_url_params(url, {"page": "1", "per_page": 100})
        if reverse:
            return self._paginated_get_reverse(url, items_selector, max_results)
        else:
            return self._paginated_get_normal(url, items_selector, max_results)

    def _paginated_get_normal(self, url, items_selector, max_results):
        while True:
            response = self.get(url)
            if not response:
                break

            json_response = response.json()
            if max_results != -1 and json_response["total_count"] > max_results:
                break

            for item in items_selector(json_response):
                yield item

            if "next" in response.links:
                url = response.links["next"]["url"]
            else:
                break

    def _paginated_get_reverse(self, url, items_selector, max_results):
        first_url = url
        first_response = self.get(url)
        if not first_response:
            return
        first_json_response = first_response.json()
        if max_results != -1 and first_json_response["total_count"] > max_results:
            return

        if "last" in first_response.links:
            url = first_response.links["last"]["url"]

        while True:
            if url != first_url:
                response = self.get(url)
                if not response:
                    break
                json_response = response.json()
            else:
                response = first_response
                json_response = first_json_response

            for item in list(items_selector(json_response))[::-1]:
                yield item

            if "prev" in response.links:
                url = response.links["prev"]["url"]
            else:
                break

    @staticmethod
    def _add_url_params(url, params):
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urlencode(query)
        return urlparse.urlunparse(url_parts)
