class GithubRepository(object):
    def __init__(self, repo_id, name, commits_url):
        self.commits_url = commits_url
        self.name = name
        self.id = repo_id


class GithubCommit(object):
    def __init__(self, commit_id, api_url, html_url):
        self.html_url = html_url
        self.api_url = api_url
        self.id = commit_id

