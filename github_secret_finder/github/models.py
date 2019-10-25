from datetime import datetime, timedelta


class GithubBranch(object):
    def __init__(self, name, sha):
        self.sha = sha
        self.name = name

    def get_commits_url(self, repo: 'GithubRepository', since: datetime = None):
        url = "https://api.github.com/repos/%s/commits?sha=%s" % (repo.name, self.sha)
        if since is not None:
            url += "&since=" + since.strftime("%Y-%m-%dT%H:%M:%SZ")
        return url

    @staticmethod
    def from_json(json) -> 'GithubBranch':
        return GithubBranch(json["name"], json["commit"]["sha"])


class GithubRepository(object):
    def __init__(self, name: str, default_branch: str, is_fork: bool, parent: 'GithubRepository'):
        self.name = name
        self.default_branch = default_branch
        self.parent = parent
        self.is_fork = is_fork

    def get_branches_url(self):
        return "https://api.github.com/repos/%s/branches" % self.name

    def get_contributors_url(self):
        return "https://api.github.com/repos/%s/contributors" % self.name

    def get_compare_url(self, base: GithubBranch, head: GithubBranch, compare_with_parent=False):
        if compare_with_parent:
            return "https://api.github.com/repos/%s/compare/%s...%s:%s" % (self.parent.name, base.name, self.name.split("/")[0], head.name)
        else:
            return "https://api.github.com/repos/%s/compare/%s...%s" % (self.name, base.name, head.name)

    @staticmethod
    def from_json(json) -> 'GithubRepository':
        parent = None
        if "parent" in json:
            parent = GithubRepository.from_json(json["parent"])
        return GithubRepository(json["full_name"], json["default_branch"], json["fork"], parent)


class GithubCommit(object):
    def __init__(self, sha, api_url, html_url, date: datetime):
        self.date = date
        self.html_url = html_url
        self.api_url = api_url
        self.sha = sha

    def __str__(self):
        return "%s (%s)" % (self.sha, self.date)

    @staticmethod
    def from_json(json) -> 'GithubCommit':
        return GithubCommit(json["sha"], json["url"], json["html_url"], GithubCommit._parse_date(json["commit"]["committer"]["date"]))

    @staticmethod
    def _parse_date(s):
        if len(s) >= 25:
            return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S") + (1 if s[19] == '-' else -1) * timedelta(hours=int(s[20:22]), minutes=int(s[23:25]))
        else:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")

class GithubUser(object):
    def __init__(self, login, name, url, repos_url):
        self.login = login
        self.repos_url = repos_url
        self.url = url
        self.name = name

    @staticmethod
    def from_json(json) -> 'GithubUser':
        return GithubUser(json["login"], json["name"], json["url"], json["repos_url"])
