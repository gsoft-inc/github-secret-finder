from datetime import datetime, timedelta
import email.utils as eut


class GithubTokenRateLimitInformation(object):
    def __init__(self, token):
        self.token = token
        self.limit = 30
        self.remaining = 30
        self.reset_time = datetime.now() + timedelta(seconds=60)

    def update(self, response):
        server_now = datetime(*eut.parsedate(response.headers["date"])[:6])

        if "X-RateLimit-Reset" in response.headers:
            reset_offset = datetime.utcfromtimestamp(int(response.headers["X-RateLimit-Reset"])) - server_now
            self.reset_time = datetime.utcnow() + reset_offset
            self.remaining = int(response.headers["X-RateLimit-Remaining"])
            self.limit = int(response.headers["X-RateLimit-Limit"])

