import operator
import requests
import time
import email.utils as eut
from datetime import datetime, timedelta


class GithubTokenRateLimitInformation(object):
    def __init__(self, token):
        self.token = token
        self.limit = 30
        self.remaining = 30
        self.reset_time = datetime.now() + timedelta(seconds=60)

    def update(self, response):
        server_now = datetime(*eut.parsedate(response.headers["date"])[:6])
        reset_offset = datetime.utcfromtimestamp(int(response.headers["X-RateLimit-Reset"])) - server_now
        self.reset_time = datetime.utcnow() + reset_offset
        self.remaining = int(response.headers["X-RateLimit-Remaining"])
        self.limit = int(response.headers["X-RateLimit-Limit"])


class GithubRateLimitedRequester(object):
    _throttle_messages = ["API rate limit exceeded", "abuse detection mechanism"]

    def __init__(self, tokens):
        self._token_infos = []
        for t in tokens:
            self._token_infos.append(GithubTokenRateLimitInformation(t))

    def get(self, url):
        while True:
            for token_info in sorted(self._token_infos, key=operator.attrgetter("remaining"), reverse=True):
                headers = {
                    'Accept': 'application/vnd.github.cloak-preview',
                    'Authorization': "token " + token_info.token
                }

                if token_info.remaining == 0 and token_info.reset_time > datetime.utcnow():
                    continue

                response = requests.get(url, headers=headers)
                token_info.update(response)

                if response.status_code == 403:
                    json_response = response.json()
                    if "message" in json_response and any(m for m in self._throttle_messages if m in json_response["message"]):
                        # Throttling error. Try the next token.
                        continue

                return response

            sleep_time = (min([t.reset_time for t in self._token_infos]) - datetime.utcnow()).total_seconds() + 1
            if sleep_time > 0:
                print("Sleeping %d seconds" % sleep_time)
                time.sleep(sleep_time)

    def paginated_get(self, url):
        while True:
            response = self.get(url)
            if response.status_code != 200:
                break

            for item in response.json()["items"]:
                yield item

            links = self.parse_link_headers(response.headers)
            if "next" in links:
                url = links["next"]
            else:
                break

    @staticmethod
    def parse_link_headers(headers):
        links = {}
        if "link" in headers:
            for linkHeader in headers["link"].split(", "):
                (url, rel) = linkHeader.split("; ")
                url = url[1:-1]
                rel = rel[5:-1]
                links[rel] = url
        return links
