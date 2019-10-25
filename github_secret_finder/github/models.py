class GithubRepository(object):
    def __init__(self, repo_id, name, commits_url, branches_url, contributors_url, compare_url, is_fork):
        self.contributors_url = contributors_url
        self.branches_url = branches_url
        self.commits_url = commits_url
        self.name = name
        self.id = repo_id
        self.compare_url = compare_url
        self.is_fork = is_fork


class GithubBranch(object):
    def __init__(self, name, sha, commits_url):
        self.sha = sha
        self.name = name
        self.commits_url = commits_url


class GithubCommit(object):
    def __init__(self, commit_id, api_url, html_url, date):
        self._date = date
        self.html_url = html_url
        self.api_url = api_url
        self.id = commit_id


class GithubUser(object):
    def __init__(self, login, name, url, repos_url):
        self.login = login
        self.repos_url = repos_url
        self.url = url
        self.name = name
