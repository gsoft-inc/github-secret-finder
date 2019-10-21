import uuid
from analysis import PatchAnalyzer
from github import GithubApiClient, CachedGithubSearchClient, GithubSearchClient
from sqlitedict import SqliteDict
import logging


class SecretFinder(object):
    def __init__(self, tokens, db_file, blacklist_file):
        self._db_file = db_file
        self._search = CachedGithubSearchClient(GithubSearchClient(tokens), db_file, "queries")
        self._api = GithubApiClient(tokens)
        self._patch_analyzer = PatchAnalyzer(blacklist_file)

    def __enter__(self):
        if not hasattr(self, '_commits_db') or self._commits_db is None:
            self._commits_db = SqliteDict(self._db_file, tablename="analyzed_commits", autocommit=True)

        if not hasattr(self, '_findings_db') or self._findings_db is None:
            self._findings_db = SqliteDict(self._db_file, tablename="findings", autocommit=True)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._commits_db.close()
        self._findings_db.close()

    def find_by_username(self, username):
        for qualifier in ["committer", "author"]:
            for r in self._find("%s:%s" % (qualifier, username)):
                yield r

    def find_by_name(self, name):
        for qualifier in ["committer-name", "author-name"]:
            for r in self._find("%s:\"%s\"" % (qualifier, name)):
                yield r

    def find_by_email(self, email):
        for qualifier in ["committer-email", "author-email"]:
            for r in self._find("%s:%s" % (qualifier, email)):
                yield r

    def _find(self, query):
        logging.info("Query: %s" % query)
        for commit, url, html_url in self._search.search_commits(query):
            if commit in self._commits_db:
                continue

            patch = self._api.get_commit_patch(url)
            if not patch:
                continue

            logging.info(html_url)

            for secret in self._patch_analyzer.find_secrets(patch):
                result = {"url": url, "html_url": html_url, "secret": secret}
                yield result
                self._findings_db[str(uuid.uuid4())] = result

            self._commits_db[commit] = None
