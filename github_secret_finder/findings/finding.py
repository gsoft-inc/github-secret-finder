from analysis import Secret
from github.models import GithubCommit


class Finding(object):
    def __init__(self, commit: GithubCommit, secret: Secret):
        self.commit = commit
        self.secret = secret
        self.notification_sent = False